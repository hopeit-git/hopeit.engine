"""Endpoint to run predictions and store a datablock"""

import uuid
from dataframes_example.iris import (
    IrisBatchPredictionRequest,
    IrisFeatures,
    IrisOfflinePredictionDataBlock,
)
from dataframes_example.model_storage import load_experiment_model

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.dataframes import DataFrames, DataBlocks

from sklearn.tree import DecisionTreeClassifier  # type: ignore

__steps__ = ["predict"]


__api__ = event_api(
    summary="Predict Offline",
    query_args=[("experiment_id", str)],
    payload=(IrisBatchPredictionRequest, "Batch of prediction requests"),
    responses={200: IrisOfflinePredictionDataBlock},
)


async def predict(
    request: IrisBatchPredictionRequest, context: EventContext, *, experiment_id: str
) -> IrisOfflinePredictionDataBlock:
    """Loads model and predict based on request features"""
    model: DecisionTreeClassifier = await load_experiment_model(experiment_id, context)

    df = DataFrames.df(
        DataFrames.from_dataobjects(IrisFeatures, (item.features for item in request.items))
    )

    df["variety"] = model.predict(df)

    return await DataBlocks.save(IrisOfflinePredictionDataBlock, df, batch_id=uuid.uuid4().hex)
