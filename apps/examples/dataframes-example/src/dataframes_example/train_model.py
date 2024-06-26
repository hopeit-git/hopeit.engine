"""Example training pipeline for the Iris dataset
"""

# pylint: disable=invalid-name

import uuid
from datetime import datetime, timezone

from hopeit.dataframes.serialization.dataset import Dataset
import pandas as pd
from dataframes_example import experiment_storage, model_storage
from dataframes_example.iris import (
    EvalMetrics,
    Experiment,
    InputData,
    Iris,
    IrisFeatures,
    IrisLabels,
)
from hopeit.app.api import event_api
from hopeit.app.context import EventContext, PostprocessHook
from hopeit.app.logger import app_extra_logger
from hopeit.dataframes import DataFrames
from hopeit.server.steps import SHUFFLE

from sklearn.metrics import accuracy_score  # type: ignore
from sklearn.model_selection import train_test_split  # type: ignore
from sklearn.tree import DecisionTreeClassifier  # type: ignore

logger, extra = app_extra_logger()

__steps__ = [
    "prepare_experiment",
    SHUFFLE,
    "prepare_datasets",
    SHUFFLE,
    "train_model",
    SHUFFLE,
    "evaluate_model",
    SHUFFLE,
    "save_experiment",
]


__api__ = event_api(
    summary="Training Pipeline",
    payload=(InputData, "Serialized dataframeobject with iris dataset"),
    responses={200: Iris},
)


def prepare_experiment(input_data: InputData, context: EventContext) -> Experiment:
    experiment_id = str(uuid.uuid4())

    logger.info(
        context, "Setting up experiment", extra=extra(experiment_id=experiment_id)
    )

    return Experiment(
        experiment_id=experiment_id,
        experiment_dt=datetime.now(tz=timezone.utc),
        input_data=input_data.iris,
    )


# async def __postprocess__(
#     experiment: Experiment, context: EventContext, response: PostprocessHook
# ) -> Experiment:
#     return experiment


async def prepare_datasets(experiment: Experiment, context: EventContext) -> Experiment:
    """Split training and test datasets"""
    logger.info(
        context,
        "Preparing feature and label datasets",
        extra=extra(experiment_id=experiment.experiment_id),
    )

    input_data: Iris = await experiment.input_data.load()
    X = DataFrames.from_dataframe(IrisFeatures, input_data)
    y = DataFrames.from_dataframe(IrisLabels, input_data)

    X_train, X_test, y_train, y_test = train_test_split(
        DataFrames.df(X), DataFrames.df(y), test_size=0.2, random_state=42
    )

    experiment.train_features = await Dataset.save(
        DataFrames.from_df(IrisFeatures, X_train)
    )
    experiment.train_labels = await Dataset.save(
        DataFrames.from_df(IrisLabels, y_train)
    )
    experiment.test_features = await Dataset.save(
        DataFrames.from_df(IrisFeatures, X_test)
    )
    experiment.test_labels = await Dataset.save(
        DataFrames.from_df(IrisLabels, y_test)
    )
    return experiment


async def train_model(experiment: Experiment, context: EventContext) -> Experiment:
    """Trains DecisionTreeClassifier"""

    logger.info(
        context,
        "Training model...",
        extra=extra(experiment_id=experiment.experiment_id),
    )

    train_features: IrisFeatures = await experiment.train_features.load()
    train_labels: IrisLabels = await experiment.train_labels.load()

    clf = DecisionTreeClassifier(random_state=42)
    clf.fit(
        DataFrames.df(train_features), DataFrames.df(train_labels)
    )

    logger.info(
        context,
        "Saving model...",
        extra=extra(
            experiment_id=experiment.experiment_id,
        ),
    )
    experiment.saved_model_location = await model_storage.save_model(
        clf, experiment.experiment_id, context
    )

    return experiment


async def evaluate_model(experiment: Experiment, context: EventContext) -> Experiment:
    """Evaluates trained model score usint test dataset"""
    logger.info(
        context,
        "Loading model...",
        extra=extra(
            experiment_id=experiment.experiment_id,
            model_location=experiment.saved_model_location,
        ),
    )

    assert experiment.saved_model_location is not None

    clf: DecisionTreeClassifier = await model_storage.load_model(
        experiment.saved_model_location, context
    )

    logger.info(
        context,
        "Evaluating model...",
        extra=extra(experiment_id=experiment.experiment_id),
    )

    test_features: IrisFeatures = await experiment.test_features.load()
    test_labels: IrisLabels = await experiment.test_labels.load()

    y = clf.predict(DataFrames.df(test_features))
    pred_labels = IrisLabels(variety=pd.Series(y))
    accuracy = accuracy_score(
        DataFrames.df(test_labels), DataFrames.df(pred_labels)
    )

    experiment.eval_metrics = EvalMetrics(accuracy_score=accuracy)
    return experiment


async def save_experiment(experiment: Experiment, context: EventContext) -> Experiment:
    """Save experiment results"""
    logger.info(
        context,
        "Saving experiment...",
        extra=extra(experiment_id=experiment.experiment_id),
    )

    location = await experiment_storage.save_experiment(experiment, context)

    logger.info(
        context,
        "Experiment saved.",
        extra=extra(experiment_id=experiment.experiment_id, location=location),
    )

    return experiment
