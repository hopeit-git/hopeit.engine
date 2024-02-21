"""
Simple Example: Setup Something
--------------------------------------------------------------------
SETUP EventType runs before initializing endpoints, streams, and services.
"""

from pathlib import Path

from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger


__steps__ = ["run_once"]


logger, extra = app_extra_logger()


async def run_once(payload: None, context: EventContext):
    """
    This method initializes the environment.
    """
    logger.info(context, "Setup done")
    Path("/tmp/hopeit.initialized").touch()
