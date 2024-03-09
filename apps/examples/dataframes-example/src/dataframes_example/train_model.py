import uuid
from datetime import datetime, timezone

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
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier

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


def __postprocess__(
    experiment: Experiment, context: EventContext, response: PostprocessHook
) -> Experiment:
    return experiment.serialize()


def prepare_datasets(experiment: Experiment, context: EventContext) -> Experiment:
    logger.info(
        context,
        "Preparing feature and label datasets",
        extra=extra(experiment_id=experiment.experiment_id),
    )

    X = IrisFeatures.from_df(experiment.input_data.df)
    y = IrisLabels.from_df(experiment.input_data.df)

    X_train, X_test, y_train, y_test = train_test_split(
        X.df, y.df, test_size=0.2, random_state=42
    )

    experiment.train_features = IrisFeatures.from_df(X_train)
    experiment.train_labels = IrisLabels.from_df(y_train)
    experiment.test_features = IrisFeatures.from_df(X_test)
    experiment.test_labels = IrisLabels.from_df(y_test)

    return experiment


async def train_model(experiment: Experiment, context: EventContext) -> Experiment:

    logger.info(
        context,
        "Training model...",
        extra=extra(experiment_id=experiment.experiment_id),
    )

    clf = DecisionTreeClassifier(random_state=42)
    clf.fit(experiment.train_features.df, experiment.train_labels.df)

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

    clf: DecisionTreeClassifier = await model_storage.load_model(
        experiment.model_location, context
    )

    logger.info(
        context,
        "Evaluating model...",
        extra=extra(experiment_id=experiment.experiment_id),
    )

    y = clf.predict(experiment.test_features.df)
    pred_labels = IrisLabels(variety=pd.Series(y))
    accuracy = accuracy_score(experiment.test_labels.df, pred_labels.df)

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
