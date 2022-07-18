import asyncio
import os
import sys
from typing import Optional

import sniffio
from anyio.abc import TaskStatus
from typing_extensions import Literal

from prefect.infrastructure.base import Infrastructure, InfrastructureResult
from prefect.utilities.processutils import run_process


def _use_threaded_child_watcher():
    if (
        sys.version_info < (3, 8)
        and sniffio.current_async_library() == "asyncio"
        and sys.platform != "win32"
    ):
        from prefect.utilities.compat import ThreadedChildWatcher

        # Python < 3.8 does not use a `ThreadedChildWatcher` by default which can
        # lead to errors in tests on unix as the previous default `SafeChildWatcher`
        # is not compatible with threaded event loops.
        asyncio.get_event_loop_policy().set_child_watcher(ThreadedChildWatcher())


class Process(Infrastructure):
    type: Literal["subprocess"] = "subprocess"
    stream_output: bool = True

    async def run(
        self,
        task_status: TaskStatus = None,
    ) -> Optional[bool]:
        if not self.command:
            raise ValueError("Process cannot be run with empty command.")

        _use_threaded_child_watcher()
        display_name = f" {self.name!r}" or ""

        # Open a subprocess to execute the flow run
        self.logger.info(f"Opening process{display_name}...")
        self.logger.debug(
            f"Process{display_name} running command: {' '.join(self.command)}"
        )

        process = await run_process(
            self.command,
            stream_output=self.stream_output,
            task_status=task_status,
            # The base environment must override the current environment or
            # the Prefect settings context may not be respected
            env={**os.environ, **self._base_environment(), **self.env},
        )

        # Use the pid for display if no name was given
        display_name = display_name or f" {process.pid}"

        if process.returncode:
            self.logger.error(
                f"Process{display_name} exited with status code: "
                f"{process.returncode}"
            )
        else:
            self.logger.info(f"Process{display_name} exited cleanly.")

        return ProcessResult(status_code=process.returncode, identifier=process.pid)


class ProcessResult(InfrastructureResult):
    """Contains information about the final state of a completed process"""
