"""Prepares input data for training pipeline
"""

from dataframes_example.iris import InputData, Iris
from dataframes_example.settings import DataStorage
from hopeit.dataframes.serialization.dataset import Dataset
from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from hopeit.dataframes import DataFrames
from hopeit.dataobjects import fields
from hopeit.dataobjects.payload import Payload
from sklearn import datasets

from hopeit.server.steps import SHUFFLE  # type: ignore

logger, extra = app_extra_logger()

__steps__ = [
    "download_data",
    "save_raw_data",
    SHUFFLE,
    "check"
]

__api__ = event_api(summary="Prepare Data", responses={200: InputData})


def download_data(payload: None, context: EventContext) -> Iris:
    """Downloads training data using scikit-learn"""

    logger.info(context, "Downloading input data..")

    raw = datasets.load_iris(as_frame=True)

    iris = DataFrames.from_df(
        Iris,
        raw.frame.rename(
            columns={
                field.serialization_alias: field_name
                for field_name, field in fields(Iris).items()  # type: ignore[type-var]
            }
        ),
    )

    return iris


async def save_raw_data(iris: Iris, context: EventContext) -> InputData:
    settings: DataStorage = context.settings(key="data_storage", datatype=DataStorage)

    logger.info(context, "Saving input data..", extra=extra(**Payload.to_obj(settings)))  # type: ignore[arg-type]

    return InputData(
        iris = await Dataset.save(iris)   
    )


# TODO: remove step
async def check(input_data: InputData, context: EventContext) -> Iris:
    iris = await input_data.iris.load()
    print(DataFrames.df(iris))
    return DataFrames.to_dataobjects(iris)
