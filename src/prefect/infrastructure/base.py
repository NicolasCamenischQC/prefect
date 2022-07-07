import abc
from typing import Dict, List, Optional

import pydantic
from anyio.abc import TaskStatus
from typing_extensions import Literal

from prefect.blocks.core import Block
from prefect.logging import get_logger
from prefect.utilities.pydantic import lookup_type


class Infrastructure(Block, abc.ABC):
    _block_schema_capabilities = ["run"]

    type: str

    env: Dict[str, str] = pydantic.Field(default_factory=dict)
    labels: Dict[str, str] = pydantic.Field(default_factory=dict)
    name: Optional[str] = None
    command: List[str] = None

    @abc.abstractmethod
    async def run(
        self,
        task_status: TaskStatus = None,
    ) -> Optional[bool]:
        """
        Run the infrastructure, reporting a `task_status.started()` when the
        infrastructure is created and returning a `bool` at the end indicating if the
        infrastructure exited cleanly or encountered an error.
        """

    @property
    def logger(self):
        return get_logger(f"prefect.infrastructure.{self.type}")


class AnyInfrastructure(Infrastructure):
    """
    Placeholder infrastructure type. The actual type will be determined by the caller.
    """

    type: Literal["any"] = "any"

    async def run(
        self,
        type: str,
        task_status: TaskStatus = None,
    ) -> Optional[bool]:
        runtime_type = lookup_type(Infrastructure, type)
        runtime_inst = runtime_type(
            env=self.env, labels=self.labels, name=self.name, command=self.command
        )
        return await runtime_inst(task_status=task_status)
