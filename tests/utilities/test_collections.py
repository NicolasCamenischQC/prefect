import json
import uuid
from dataclasses import dataclass
from typing import Any

import pydantic
import pytest

from prefect.utilities.collections import (
    AutoEnum,
    dict_to_flatdict,
    flatdict_to_dict,
    remove_nested_keys,
    visit_collection,
)


class Color(AutoEnum):
    RED = AutoEnum.auto()
    BLUE = AutoEnum.auto()


class TestAutoEnum:
    async def test_autoenum_generates_string_values(self):
        assert Color.RED.value == "RED"
        assert Color.BLUE.value == "BLUE"

    async def test_autoenum_repr(self):
        assert repr(Color.RED) == str(Color.RED) == "Color.RED"

    async def test_autoenum_can_be_json_serialized_with_default_encoder(self):
        json.dumps(Color.RED) == "RED"


class TestFlatDict:
    @pytest.fixture
    def nested_dict(self):
        return {1: 2, 2: {1: 2, 3: 4}, 3: {1: 2, 3: {4: 5, 6: {7: 8}}}}

    def test_dict_to_flatdict(self, nested_dict):
        assert dict_to_flatdict(nested_dict) == {
            (1,): 2,
            (2, 1): 2,
            (2, 3): 4,
            (3, 1): 2,
            (3, 3, 4): 5,
            (3, 3, 6, 7): 8,
        }

    def test_flatdict_to_dict(self, nested_dict):
        assert flatdict_to_dict(dict_to_flatdict(nested_dict)) == nested_dict


async def negative_even_numbers(x):
    print("Function called on", x)
    if isinstance(x, int) and x % 2 == 0:
        return -x
    return x


EVEN = set()


async def visit_even_numbers(x):
    if isinstance(x, int) and x % 2 == 0:
        EVEN.add(x)
    return x


VISITED = list()


async def add_to_visited_list(x):
    VISITED.append(x)


@pytest.fixture(autouse=True)
def clear_sets():
    EVEN.clear()
    VISITED.clear()


@dataclass
class SimpleDataclass:
    x: int
    y: int


class SimplePydantic(pydantic.BaseModel):
    x: int
    y: int


class ExtraPydantic(pydantic.BaseModel):
    x: int

    class Config:
        extra = pydantic.Extra.allow


class PrivatePydantic(pydantic.BaseModel):
    """Pydantic model with private attrs"""

    x: int
    _y: int
    _z: Any = pydantic.PrivateAttr()

    class Config:
        underscore_attrs_are_private = True
        extra = pydantic.Extra.forbid  # Forbid extras to raise in tests


class ImmutablePrivatePydantic(PrivatePydantic):
    class Config:
        allow_mutation = False


@dataclass
class Foo:
    x: Any


@dataclass
class Bar:
    y: Any
    z: int = 2


class TestPydanticObjects:
    """
    Checks that the Pydantic test objects defined in this file behave as expected.

    These tests do not cover Prefect functionality and may break if Pydantic introduces
    breaking changes.
    """

    async def test_private_pydantic_behaves_as_expected(self):
        input = PrivatePydantic(x=1)

        # Public attr accessible immediately
        assert input.x == 1
        # Extras not allowed
        with pytest.raises(ValueError):
            input._a = 1
        # Private attr not accessible until set
        with pytest.raises(AttributeError):
            input._y

        # Private attrs accessible after setting
        input._y = 4
        input._z = 5
        assert input._y == 4
        assert input._z == 5

    async def test_immutable_pydantic_behaves_as_expected(self):

        input = ImmutablePrivatePydantic(x=1)

        # Public attr accessible immediately
        assert input.x == 1
        # Extras not allowed
        with pytest.raises(ValueError):
            input._a = 1
        # Private attr not accessible until set
        with pytest.raises(AttributeError):
            input._y

        # Private attrs accessible after setting
        input._y = 4
        input._z = 5
        assert input._y == 4
        assert input._z == 5

        # Mutating not allowed
        with pytest.raises(TypeError):
            input.x = 2

        # Can still mutate private attrs
        input._y = 6


class TestVisitCollection:
    @pytest.mark.parametrize(
        "inp,expected",
        [
            (3, 3),
            (4, -4),
            ([3, 4], [3, -4]),
            ((3, 4), (3, -4)),
            ([3, 4, [5, [6]]], [3, -4, [5, [-6]]]),
            ({3: 4, 6: 7}, {3: -4, -6: 7}),
            ({3: [4, {6: 7}]}, {3: [-4, {-6: 7}]}),
            ({3, 4, 5}, {3, -4, 5}),
            (SimpleDataclass(x=1, y=2), SimpleDataclass(x=1, y=-2)),
            (SimplePydantic(x=1, y=2), SimplePydantic(x=1, y=-2)),
            (ExtraPydantic(x=1, y=2, z=3), ExtraPydantic(x=1, y=-2, z=3)),
        ],
    )
    async def test_visit_collection_and_transform_data(self, inp, expected):
        result = await visit_collection(
            inp, visit_fn=negative_even_numbers, return_data=True
        )
        assert result == expected

    @pytest.mark.parametrize(
        "inp,expected",
        [
            (3, set()),
            (4, {4}),
            ([3, 4], {4}),
            ((3, 4), {4}),
            ([3, 4, [5, [6]]], {4, 6}),
            ({3: 4, 6: 7}, {4, 6}),
            ({3: [4, {6: 7}]}, {4, 6}),
            ({3, 4, 5}, {4}),
            (SimpleDataclass(x=1, y=2), {2}),
            (SimplePydantic(x=1, y=2), {2}),
            (ExtraPydantic(x=1, y=2, z=4), {2, 4}),
        ],
    )
    async def test_visit_collection(self, inp, expected):
        result = await visit_collection(
            inp, visit_fn=visit_even_numbers, return_data=False
        )
        assert result is None
        assert EVEN == expected

    @pytest.mark.parametrize(
        "inp,expected",
        [
            ({"x": 1}, [{"x": 1}, "x", 1]),
            (SimpleDataclass(x=1, y=2), [SimpleDataclass(x=1, y=2), 1, 2]),
        ],
    )
    async def test_visit_collection_visits_nodes(self, inp, expected):
        result = await visit_collection(
            inp, visit_fn=add_to_visited_list, return_data=False
        )
        assert result is None
        assert VISITED == expected

    async def test_visit_collection_allows_mutation_of_nodes(self):
        async def collect_and_drop_x_from_dicts(node):
            await add_to_visited_list(node)
            if isinstance(node, dict):
                return {key: value for key, value in node.items() if key != "x"}
            return node

        result = await visit_collection(
            {"x": 1, "y": 2}, visit_fn=collect_and_drop_x_from_dicts, return_data=True
        )
        assert result == {"y": 2}
        assert VISITED == [{"x": 1, "y": 2}, "y", 2]

    async def test_visit_collection_with_private_pydantic_attributes(self):
        """
        We should not visit private fields on Pydantic models.
        """
        input = PrivatePydantic(x=2)
        input._y = 3
        input._z = 4

        result = await visit_collection(
            input, visit_fn=visit_even_numbers, return_data=False
        )
        assert EVEN == {2}, "Only the public field should be visited"
        assert result is None, "Data should not be returned"

        # The original model should not be mutated
        assert input._y == 3
        assert input._z == 4

    async def test_visit_collection_includes_unset_pydantic_fields(self):
        class RandomPydantic(pydantic.BaseModel):
            val: uuid.UUID = pydantic.Field(default_factory=uuid.uuid4)

        input_model = RandomPydantic()
        output_model = await visit_collection(
            input_model, visit_fn=visit_even_numbers, return_data=True
        )

        assert (
            output_model.val == input_model.val
        ), "The fields value should be used, not the default factory"

    @pytest.mark.parametrize("immutable", [True, False])
    async def test_visit_collection_mutation_with_private_pydantic_attributes(
        self, immutable
    ):
        model = ImmutablePrivatePydantic if immutable else PrivatePydantic
        input = model(x=2)
        input._y = 3
        input._z = 4

        result = await visit_collection(
            input, visit_fn=negative_even_numbers, return_data=True
        )

        assert result.x == -2, "The public attribute should be modified"

        # Pydantic dunders are retained
        assert result.__private_attributes__ == input.__private_attributes__
        assert result.__fields__ == input.__fields__
        assert result.__fields_set__ == input.__fields_set__

        # Private attributes are retained without modification
        assert result._y == 3
        assert result._z == 4

    @pytest.mark.parametrize("return_data", [True, False])
    async def test_visit_collection_avoids_infinite_recursion(self, return_data):
        async def identity(expr):
            print(expr)
            return expr

        @dataclass
        class Foo:
            x: Any

        @dataclass
        class Bar:
            y: Any

        # Create references to eachother
        foo = Foo(x=None)
        bar = Bar(y=foo)
        foo.x = bar

        result = await visit_collection(foo, visit_fn=identity, return_data=return_data)
        if not return_data:
            assert result is None
        else:
            assert result == foo

    async def test_visit_collection_transforms_correctly_with_revisit(self):
        """
        When there is a recursive relationship, the object will be fully resolved in
        one place and ignored in the other then the collections will be traversed a
        second time to perform an update on the ignored item
        """
        # Create references to each other
        foo = Foo(x=None)
        bar = Bar(y=foo)
        foo.x = bar

        result = await visit_collection(
            [foo, bar], visit_fn=negative_even_numbers, return_data=True
        )
        expected_foo = Foo(x=None)
        expected_bar = Bar(y=foo, z=-2)
        expected_foo.x = expected_bar

        assert result == [expected_foo, expected_bar]


class TestRemoveKeys:
    def test_remove_single_key(self):
        obj = {"a": "a", "b": "b", "c": "c"}
        assert remove_nested_keys(["a"], obj) == {"b": "b", "c": "c"}

    def test_remove_multiple_keys(self):
        obj = {"a": "a", "b": "b", "c": "c"}
        assert remove_nested_keys(["a", "b"], obj) == {"c": "c"}

    def test_remove_keys_recursively(self):
        obj = {
            "title": "Test",
            "description": "This is a docstring",
            "type": "object",
            "properties": {
                "a": {"title": "A", "description": "A field", "type": "string"}
            },
            "required": ["a"],
            "block_type_name": "Test",
            "block_schema_references": {},
        }
        assert remove_nested_keys(["description"], obj) == {
            "title": "Test",
            "type": "object",
            "properties": {"a": {"title": "A", "type": "string"}},
            "required": ["a"],
            "block_type_name": "Test",
            "block_schema_references": {},
        }

    def test_passes_through_non_dict(self):
        assert remove_nested_keys(["foo"], 1) == 1
        assert remove_nested_keys(["foo"], "foo") == "foo"
        assert remove_nested_keys(["foo"], b"foo") == b"foo"
