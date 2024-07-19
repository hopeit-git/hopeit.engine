"""Retrieves stored experiment"""

from typing import Union

from dataframes_example.iris import (
    Experiment,
)
from dataframes_example.experiment_storage import load_experiment

from hopeit.app.api import event_api
from hopeit.app.context import EventContext, PostprocessHook

__steps__ = ["retrieve_experiment"]

__api__ = event_api(
    summary="Experiment",
    query_args=[("experiment_id", str), ("experiment_partition_key", str)],
    responses={
        200: Experiment,
        404: str,
    },
)


async def retrieve_experiment(
    payload: None, context: EventContext, *, experiment_id: str, experiment_partition_key
) -> Experiment:
    """Loads stored experiment"""
    return await load_experiment(experiment_id, experiment_partition_key, context)


def __postprocess__(
    experiment: Experiment, context: EventContext, response: PostprocessHook
) -> Union[Experiment, str]:
    if experiment is None:
        response.status = 404
        return "Experiment not found"
    return experiment
