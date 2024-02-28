
from dataclasses import asdict, fields
from dataframes_example.iris import InputData, Iris
from dataframes_example.settings import DataStorage

from hopeit.app.api import event_api
from hopeit.app.context import EventContext
from hopeit.app.logger import app_extra_logger
from hopeit.server.steps import SHUFFLE

from sklearn import datasets

logger, extra = app_extra_logger()

__steps__ = [
    "download_data",
    "save_raw_data",
]

__api__ = event_api(summary="Prepare Data", responses={200: InputData})


def download_data(payload: None, context: EventContext) -> Iris:
    logger.info(context, "Downloading input data..")

    raw = datasets.load_iris(as_frame=True)

    iris = Iris.from_df(
        raw.frame.rename(
            columns={
                field.metadata["source_field_name"]: field.name
                for field in fields(Iris)
            }
        )
    )

    return iris


async def save_raw_data(iris: Iris, context: EventContext) -> InputData:
    settings: DataStorage = context.settings(key="data_storage", datatype=DataStorage)

    logger.info(context, "Saving input data..", extra=extra(**asdict(settings)))

    return await InputData(
        iris=iris
    ).serialize()
