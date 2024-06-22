"""Dataframes example settings classes
"""

from hopeit.dataobjects import dataclass

from hopeit.dataobjects import dataobject


@dataobject
@dataclass
class DataStorage:
    ingest_data_path: str


@dataobject
@dataclass
class ModelStorage:
    path: str
