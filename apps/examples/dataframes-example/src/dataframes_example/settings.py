"""Dataframes example settings classes"""

from hopeit.dataobjects import dataclass, dataobject


@dataobject
@dataclass
class ModelStorage:
    path: str
