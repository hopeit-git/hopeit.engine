"""Simple storage for trained models using fs-storage"""

import io
import os
import pickle
from pathlib import Path
from typing import Optional, Tuple, TypeVar

import aiofiles
from dataframes_example.settings import ModelStorage
from hopeit.app.context import EventContext
from hopeit.dataobjects.payload import Payload
from hopeit.server.logger import engine_extra_logger

logger, extra = engine_extra_logger()

model_storage: Optional[ModelStorage] = None

ModelT = TypeVar("ModelT")


async def init_model_storage(context: EventContext):
    global model_storage
    model_storage = context.settings(key="model_storage", datatype=ModelStorage)
    assert model_storage is not None
    logger.info(
        context,
        "Initializing model storage...",
        extra=extra(**Payload.to_obj(model_storage)),  # type: ignore[arg-type]
    )


async def save_model(model: ModelT, experiment_id: str, context: EventContext) -> str:
    model_path, model_location, model_location_str = _get_model_location(experiment_id)

    os.makedirs(model_path, exist_ok=True)
    async with aiofiles.open(model_location, "wb") as f:
        await f.write(pickle.dumps(model, protocol=5))

    return model_location_str


async def load_model(model_location: str, context: EventContext) -> ModelT:
    async with aiofiles.open(Path(model_location), "rb") as f:
        buffer = io.BytesIO(await f.read())
        return pickle.load(buffer)


async def load_experiment_model(experiment_id: str, context: EventContext) -> ModelT:
    _, _, model_location_str = _get_model_location(experiment_id)
    return await load_model(model_location_str, context)


def _get_model_location(experiment_id: str) -> Tuple[Path, Path, str]:
    assert model_storage is not None
    model_path = Path(model_storage.path)
    model_location = model_path / f"model_{experiment_id}.pkl5"
    return model_path, model_location, model_location.as_posix()
