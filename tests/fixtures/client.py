import pytest

from prefect import flow
from prefect.client import get_client


@pytest.fixture
async def orion_client():
    async with get_client() as client:
        yield client


@pytest.fixture(autouse=True)
async def assert_lifespan_is_not_left_open():
    # This fixture checks for regressions where the application lifespan is left open
    # across tests.
    from prefect.client import APP_LIFESPANS

    yield

    assert not APP_LIFESPANS, "Lifespans should be cleared at the end of each test."


@pytest.fixture(scope="module")
def flow_function():
    @flow
    def example_flow(param=1):
        return param

    return example_flow
