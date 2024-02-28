from dataclasses import asdict
import io
import os
from pathlib import Path
import pickle
from typing import Any, Optional, TypeVar
import aiofiles

from dataframes_example.settings import ModelStorage
from hopeit.app.context import EventContext
from hopeit.server.logger import engine_extra_logger

logger, extra = engine_extra_logger()

model_storage: Optional[ModelStorage] = None

ModelType = TypeVar("ModelType")


async def init_model_storage(context: EventContext):
    global model_storage
    model_storage = context.settings(
        key="model_storage", datatype=ModelStorage
    )
    logger.info(
        context,
        f"Initializing model storage...",
        extra=extra(**asdict(model_storage)),
    )


async def save_model(model: ModelType, experiment_id: str, context: EventContext) -> str:
    model_path = Path(model_storage.path)
    model_location = model_path / f"model_{experiment_id}.pkl5"
    model_location_str = model_location.as_posix()

    os.makedirs(model_path, exist_ok=True)
    async with aiofiles.open(model_location, "wb") as f:
        await f.write(pickle.dumps(model, protocol=5))

    return model_location_str


async def load_model(model_location: str, context: EventContext) -> ModelType:
    async with aiofiles.open(Path(model_location), "rb") as f:
        buffer = io.BytesIO(await f.read())
        return pickle.load(buffer)
