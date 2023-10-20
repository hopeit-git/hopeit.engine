from dataclasses import dataclass

from hopeit.dataframes import dataframe

from hopeit.dataobjects import dataobject


@dataobject
@dataclass
class DataStorage:
    ingest_data_path: str
    data_storage_path: str


@dataobject
@dataclass
class ModelStorage:
    model_storage_path: str


@dataobject
@dataclass
class TraningParameters:
    train_test_split_ratio: float


@dataclass
class Sepal:
    length: float
    width: float


@dataclass
class Petal:
    length: float
    width: float


@dataframe
@dataclass
class Iris:
    sepal_length: float
    sepal_width: float
    petal_length: float
    petal_width: float
    variety: str
