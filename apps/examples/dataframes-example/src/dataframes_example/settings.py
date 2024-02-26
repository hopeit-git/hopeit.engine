from dataclasses import dataclass

from hopeit.dataobjects import dataobject


@dataobject
@dataclass
class DataStorage:
    ingest_data_path: str


@dataobject
@dataclass
class ModelStorage:
    model_storage_path: str
