from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import uuid

from hopeit.dataframes.serialization.dataset import Dataset
from hopeit.app.api import event_api
from hopeit.app.context import EventContext, PostprocessHook
from hopeit.dataobjects import dataobject
from hopeit.fs_storage import FileStorage, FileStorageSettings

import pandas as pd

from dataframes_example.settings import (
    DataStorage,
    ModelStorage,
)

from hopeit.dataframes import dataframe, dataframeobject
from hopeit.server.steps import SHUFFLE


__steps__ = [
    "ingest_data",
    SHUFFLE,
    "prepare_experiment",
    SHUFFLE,
    "train_model",
    SHUFFLE,
    "evaluate_model",
    SHUFFLE,
    "save_experiment",
]


@dataframe
@dataclass
class Iris:
    sepal_length: float
    sepal_width: float
    petal_length: float
    petal_width: float
    variety: str


@dataobject
@dataclass
class EvalMetrics:
    score: float


@dataframeobject
@dataclass
class Experiment:
    experiment_id: str
    experiment_dt: datetime
    train_data: Iris = None
    test_data: Iris = None
    eval_data: Iris = None
    model_location: Optional[str] = None
    eval_metrics: Optional[EvalMetrics] = None


__api__ = event_api(summary="Training Pipeline", responses={200: Iris})

fs: Optional[FileStorage] = None


async def __init_event__(context):
    global fs
    if fs is None:
        settings: FileStorageSettings = context.settings(
            key="experiment_storage", datatype=FileStorageSettings
        )
        fs = FileStorage.with_settings(settings)


def ingest_data(payload: None, context: EventContext) -> Dataset:
    settings: DataStorage = context.settings(key="data_storage", datatype=DataStorage)
    iris_df = pd.read_csv(Path(settings.ingest_data_path) / "iris.csv").rename(
        columns={
            "sepal.length": "sepal_length",
            "sepal.width": "sepal_width",
            "petal.length": "petal_length",
            "petal.width": "petal_width",
        }
    )

    iris = Iris.from_df(iris_df)
    iris.petal_length = iris.petal_width * 2 + iris.petal_length

    return iris


def prepare_experiment(input_data: Iris, context: EventContext) -> Experiment:
    test = Iris.from_df(input_data.df.sample(frac=0.1, random_state=42))
    eval = Iris.from_df(input_data.df.sample(frac=0.2, random_state=43))
    train = Iris.from_df(input_data.df.drop(test.df.index))

    return Experiment(
        experiment_id=str(uuid.uuid4()),
        experiment_dt=datetime.now(tz=timezone.utc),
        train_data=train,
        test_data=test,
        eval_data=eval,
    )


def train_model(experiment: Experiment, context: EventContext) -> Experiment:
    train: Iris = experiment.train_data
    # TODO: train model

    test: Iris = experiment.test_data
    # TODO evaluate model

    print(train.df, test.df)

    model_storage: ModelStorage = context.settings(
        key="model_storage", datatype=ModelStorage
    )
    model_location = Path(model_storage.model_storage_path) / "model.bin"

    experiment.model_location = model_location.resolve().as_posix()

    return experiment


def evaluate_model(experiment: Experiment, context: EventContext) -> Experiment:
    experiment.eval_metrics = EvalMetrics(
        score=0.0
    )
    return experiment


async def save_experiment(experiment: Experiment, context: EventContext) -> Experiment:
    await fs.store(
        key=experiment.experiment_id,
        value=await experiment.serialize(),
    )
    return experiment


# async def __postprocess__(experiment: Experiment, context: EventContext, response: PostprocessHook) -> Experiment:
#     ret = await experiment.serialize()
#     return ret

