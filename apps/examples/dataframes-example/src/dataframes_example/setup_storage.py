from dataframes_example import experiment_storage, model_storage
from hopeit.app.context import EventContext

__steps__ = [
    "init_experiment_storage",
]


async def init_experiment_storage(payload: None, context: EventContext) -> None:
    await experiment_storage.init_experiment_storage(context)
    await model_storage.init_model_storage(context)
