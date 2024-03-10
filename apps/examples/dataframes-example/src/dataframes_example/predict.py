from dataclasses import asdict, fields
from typing import List
from hopeit.dataframes import DataFrames

import pandas as pd
from dataframes_example.iris import (
    IrisBatchPredictionRequest,
    IrisBatchPredictionResponse,
    IrisFeatures,
    IrisLabels,
    IrisPredictionResponse,
)
from dataframes_example.model_storage import load_experiment_model
from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from sklearn.tree import DecisionTreeClassifier  # type: ignore

__steps__ = ["predict"]


__api__ = event_api(
    summary="Predict",
    query_args=[("experiment_id", str)],
    payload=(IrisBatchPredictionRequest, "Batch of prediction requests"),
    responses={200: List[IrisFeatures]},
)


async def predict(
    request: IrisBatchPredictionRequest, context: EventContext, *, experiment_id: str
) -> IrisBatchPredictionResponse:
    model: DecisionTreeClassifier = await load_experiment_model(experiment_id, context)

    features = DataFrames.from_dataobjects(IrisFeatures, (item.features for item in request.items))

    model_predictions = model.predict(DataFrames.df(features))

    predictions = DataFrames.from_array(IrisLabels, model_predictions)

    return IrisBatchPredictionResponse(
        items=[
            IrisPredictionResponse(
                prediction_id=request.prediction_id,
                prediction=prediction,
            )
            for request, prediction in zip(request.items, DataFrames.to_dataobjects(predictions))
        ]
    )
