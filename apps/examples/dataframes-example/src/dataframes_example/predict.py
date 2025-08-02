"""Endpoint to run predictions using trained model"""

from dataframes_example.iris import (
    IrisBatchPredictionRequest,
    IrisBatchPredictionResponse,
    IrisFeatures,
    IrisLabels,
    IrisPredictionResponse,
)
from dataframes_example.model_storage import load_experiment_model

import polars as pl

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.dataframes import DataFrames

from sklearn.tree import DecisionTreeClassifier  # type: ignore

__steps__ = ["predict"]


__api__ = event_api(
    summary="Predict",
    query_args=[("experiment_id", str)],
    payload=(IrisBatchPredictionRequest, "Batch of prediction requests"),
    responses={200: IrisBatchPredictionResponse},
)


async def predict(
    request: IrisBatchPredictionRequest, context: EventContext, *, experiment_id: str
) -> IrisBatchPredictionResponse:
    """Loads model and predict based on request features"""
    model: DecisionTreeClassifier = await load_experiment_model(experiment_id, context)

    features = DataFrames.from_dataobjects(IrisFeatures, (item.features for item in request.items))

    model_predictions = model.predict(DataFrames.df(features))

    predictions = DataFrames.from_df(
        IrisLabels, pl.from_numpy(model_predictions, schema=DataFrames.schema(IrisLabels))
    )

    return IrisBatchPredictionResponse(
        items=[  # type: ignore
            IrisPredictionResponse(
                prediction_id=request.prediction_id,
                prediction=prediction,
            )
            for request, prediction in zip(request.items, DataFrames.to_dataobjects(predictions))
        ]
    )
