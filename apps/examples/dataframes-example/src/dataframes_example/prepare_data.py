"""Prepares input data for training pipeline"""

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from hopeit.dataframes import DataFrames, Dataset
from hopeit.dataobjects import fields
from sklearn import datasets  # type: ignore

from dataframes_example.iris import InputData, Iris

logger, extra = app_extra_logger()

__steps__ = [
    "download_data",
    "save_raw_data",
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
    logger.info(context, "Saving input data..")  # type: ignore[arg-type]

    # Saving data to `default` database (no `database_key` specified)
    return InputData(iris=await Dataset.save(iris, save_schema=True))
