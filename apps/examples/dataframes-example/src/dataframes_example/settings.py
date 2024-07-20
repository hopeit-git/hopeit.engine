"""Dataframes example settings classes"""

from hopeit.dataobjects import dataclass, dataobject


@dataobject
@dataclass
class DataStorage:
    ingest_data_path: str


@dataobject
@dataclass
class ModelStorage:
    path: str
