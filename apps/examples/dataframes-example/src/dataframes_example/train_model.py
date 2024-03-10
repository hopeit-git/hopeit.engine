import uuid
from datetime import datetime, timezone
from hopeit.dataframes import DataFrames

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


async def __postprocess__(
    experiment: Experiment, context: EventContext, response: PostprocessHook
) -> Experiment:
    return await DataFrames.serialize(experiment)


def prepare_datasets(experiment: Experiment, context: EventContext) -> Experiment:
    logger.info(
        context,
        "Preparing feature and label datasets",
        extra=extra(experiment_id=experiment.experiment_id),
    )

    X = DataFrames.from_dataframe(IrisFeatures, experiment.input_data)
    y = DataFrames.from_dataframe(IrisLabels, experiment.input_data)

    X_train, X_test, y_train, y_test = train_test_split(
        DataFrames.df(X), DataFrames.df(y), test_size=0.2, random_state=42
    )

    experiment.train_features = DataFrames.from_df(IrisFeatures, X_train)
    experiment.train_labels = DataFrames.from_df(IrisLabels, y_train)
    experiment.test_features = DataFrames.from_df(IrisFeatures, X_test)
    experiment.test_labels = DataFrames.from_df(IrisLabels, y_test)

    return experiment


async def train_model(experiment: Experiment, context: EventContext) -> Experiment:

    logger.info(
        context,
        "Training model...",
        extra=extra(experiment_id=experiment.experiment_id),
    )

    clf = DecisionTreeClassifier(random_state=42)
    clf.fit(DataFrames.df(experiment.train_features), DataFrames.df(experiment.train_labels))

    logger.info(
        context,
        "Saving model...",
        extra=extra(
            experiment_id=experiment.experiment_id,
        ),
    )
    experiment.model_location = await model_storage.save_model(
        clf, experiment.experiment_id, context
    )

    return experiment


async def evaluate_model(experiment: Experiment, context: EventContext) -> Experiment:
    logger.info(
        context,
        "Loading model...",
        extra=extra(
            experiment_id=experiment.experiment_id,
            model_location=experiment.model_location,
        ),
    )

    assert experiment.model_location is not None

    clf: DecisionTreeClassifier = await model_storage.load_model(
        experiment.model_location, context
    )

    logger.info(
        context,
        "Evaluating model...",
        extra=extra(experiment_id=experiment.experiment_id),
    )

    y = clf.predict(DataFrames.df(experiment.test_features))
    pred_labels = IrisLabels(variety=pd.Series(y))
    accuracy = accuracy_score(DataFrames.df(experiment.test_labels), DataFrames.df(pred_labels))

    experiment.eval_metrics = EvalMetrics(accuracy_score=accuracy)
    return experiment


async def save_experiment(experiment: Experiment, context: EventContext) -> Experiment:
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
