from pathlib import Path

from hopeit.dataframes.serialization.dataset import Dataset
from hopeit.dataframes.serialization.fs import DatasetFsStorage
from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.events import collector_step, Collector

import pandas as pd

from dataframes_example.settings import (
    DataStorage,
    ModelStorage,
    TraningParameters,
    Iris,
)

from hopeit.dataobjects import dataclass, dataobject
from hopeit.server.steps import SHUFFLE


__api__ = event_api(summary="Training Pipeline", responses={200: str})

__steps__ = [
    "ingest_data",
    SHUFFLE,
    "dummy",
    collector_step(payload=Iris).gather(
        "test_split",
        "train_split",
    ),
    "train_model",
]

# @dataobject
# @dataclass
# class TrainingTestSplitData:
#     name: str
#     train_data: Dataset
#     test_data: Dataset


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


def dummy(payload: Iris, context: EventContext) -> Iris:
    return payload


async def test_split(collector: Collector, context: EventContext) -> Iris:
    input_data = await collector["payload"]
    return Iris.from_df(input_data.df.sample(frac=0.1, random_state=42))


async def train_split(collector: Collector, context: EventContext) -> Iris:
    input_data = await collector["payload"]
    test = await collector["test_split"]
    return Iris.from_df(input_data.df.drop(test.df.index))


# def train_test_split(input_data: Iris, context: EventContext) -> TrainingTestSplitData:
#     test = Iris.from_df(input_data.df.sample(frac=0.1, random_state=42))
#     train = Iris.from_df(input_data.df.drop(test.df.index))

#     ret =  TrainingTestSplitData(
#         name="example",
#         train_data=train.dataset(),
#         test_data=test.dataset(),
#     )
#
#     return ret


async def train_model(collector: Collector, context: EventContext) -> str:

    train: Iris = await collector["train_split"]
    # TODO: train model

    test: Iris = await collector["test_split"]
    # TODO evaluate model

    print(train.df, test.df)

    model_storage: ModelStorage = context.settings(
        key="model_storage", datatype=ModelStorage
    )
    model_location = Path(model_storage.model_storage_path) / "model.bin"

    return model_location.resolve().as_posix()
