"""Example training pipeline for the Iris dataset"""

# pylint: disable=invalid-name

import uuid
from datetime import datetime, timezone

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from hopeit.dataframes import DataFrames, Dataset
from hopeit.server.steps import SHUFFLE

import polars as pl

from sklearn.metrics import accuracy_score  # type: ignore
from sklearn.model_selection import train_test_split  # type: ignore
from sklearn.tree import DecisionTreeClassifier  # type: ignore

from dataframes_example import experiment_storage, model_storage
from dataframes_example.iris import (
    EvalMetrics,
    Experiment,
    InputData,
    Iris,
    IrisFeatures,
    IrisLabels,
)

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
    responses={200: Experiment},
)


async def prepare_experiment(input_data: InputData, context: EventContext) -> Experiment:
    """Initialize experiment"""
    experiment_id = str(uuid.uuid4())

    logger.info(context, "Setting up experiment", extra=extra(experiment_id=experiment_id))

    experiment = Experiment(
        experiment_id=experiment_id,
        experiment_dt=datetime.now(tz=timezone.utc),
        input_data=input_data.iris,
    )

    location = await experiment_storage.save_experiment(experiment, context)

    experiment.experiment_partition_key = experiment_storage.get_experiment_partition_key(
        experiment, context
    )

    logger.info(
        context,
        "Experiment prepared",
        extra=extra(
            experiment_id=experiment_id,
            experiment_partition_key=experiment.experiment_partition_key,
            location=location,
        ),
    )

    return experiment


async def prepare_datasets(experiment: Experiment, context: EventContext) -> Experiment:
    """Split training and test datasets"""
    logger.info(
        context,
        "Preparing feature and label datasets",
        extra=extra(experiment_id=experiment.experiment_id),
    )

    # Loads raw data from default database
    input_data: Iris = await Dataset.load(experiment.input_data)
    X = DataFrames.from_dataframe(IrisFeatures, input_data)
    y = DataFrames.from_dataframe(IrisLabels, input_data)

    X_train, X_test, y_train, y_test = train_test_split(
        DataFrames.df(X), DataFrames.df(y), test_size=0.2, random_state=42
    )

    # Uses database specified in header to save experiment dataframes
    database_key = context.track_ids["track.database_key"]
    experiment.train_features = await Dataset.save(
        DataFrames.from_df(IrisFeatures, X_train),
        partition_dt=experiment.experiment_dt,
        database_key=database_key,
        group_key="demo/iris",
        collection="train_data",
    )
    experiment.train_labels = await Dataset.save(
        DataFrames.from_df(IrisLabels, y_train),
        partition_dt=experiment.experiment_dt,
        database_key=database_key,
        group_key="demo/iris",
        collection="train_data",
    )
    experiment.test_features = await Dataset.save(
        DataFrames.from_df(IrisFeatures, X_test),
        partition_dt=experiment.experiment_dt,
        database_key=database_key,
        group_key="demo/iris",
        collection="test_data",
    )
    experiment.test_labels = await Dataset.save(
        DataFrames.from_df(IrisLabels, y_test),
        partition_dt=experiment.experiment_dt,
        database_key=database_key,
        group_key="demo/iris",
        collection="test_data",
    )
    return experiment


async def train_model(experiment: Experiment, context: EventContext) -> Experiment:
    """Trains DecisionTreeClassifier"""

    logger.info(
        context,
        "Training model...",
        extra=extra(experiment_id=experiment.experiment_id),
    )

    assert experiment.train_features is not None
    assert experiment.train_labels is not None

    database_key = context.track_ids["track.database_key"]
    train_features: IrisFeatures = await Dataset.load(
        experiment.train_features, database_key=database_key
    )
    train_labels: IrisLabels = await Dataset.load(
        experiment.train_labels, database_key=database_key
    )

    clf = DecisionTreeClassifier(random_state=42)
    clf.fit(DataFrames.df(train_features), DataFrames.df(train_labels))

    logger.info(
        context,
        "Saving model...",
        extra=extra(
            experiment_id=experiment.experiment_id,
        ),
    )
    experiment.trained_model_location = await model_storage.save_model(
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
            trained_model_location=experiment.trained_model_location,
        ),
    )

    assert experiment.trained_model_location is not None
    assert experiment.test_features is not None
    assert experiment.test_labels is not None

    clf: DecisionTreeClassifier = await model_storage.load_model(
        experiment.trained_model_location, context
    )

    logger.info(
        context,
        "Evaluating model...",
        extra=extra(experiment_id=experiment.experiment_id),
    )

    database_key = context.track_ids["track.database_key"]
    test_features: IrisFeatures = await Dataset.load(
        experiment.test_features, database_key=database_key
    )
    test_labels: IrisLabels = await Dataset.load(experiment.test_labels, database_key=database_key)

    y = clf.predict(DataFrames.df(test_features))
    pred_labels = IrisLabels(variety=pl.Series(y))  # type: ignore[arg-type]
    accuracy = accuracy_score(DataFrames.df(test_labels), DataFrames.df(pred_labels))

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
