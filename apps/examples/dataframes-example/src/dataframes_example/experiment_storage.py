"""Simple storage for training experiments using fs storage
"""

from typing import Optional

from dataframes_example.iris import Experiment
from hopeit.app.context import EventContext
from hopeit.dataframes import DataFrames
from hopeit.dataobjects.payload import Payload
from hopeit.fs_storage import FileStorage, FileStorageSettings
from hopeit.server.logger import engine_extra_logger

logger, extra = engine_extra_logger()

fs: Optional[FileStorage] = None


async def init_experiment_storage(context: EventContext):
    """Initializes fs storage for experiments"""
    global fs
    if fs is None:
        settings: FileStorageSettings = context.settings(
            key="experiment_storage", datatype=FileStorageSettings
        )
        logger.info(
            context,
            "Initializing experiment storage...",
            extra=extra(**Payload.to_obj(settings)),  # type: ignore[arg-type]
        )
        fs = FileStorage.with_settings(settings)


async def save_experiment(experiment: Experiment, context: EventContext) -> str:
    assert fs is not None
    return await fs.store(
        key=experiment.experiment_id,
        value=experiment,
    )
