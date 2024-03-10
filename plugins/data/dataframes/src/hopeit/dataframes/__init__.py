from typing import Dict, Generic, Iterator, List, Type
from hopeit.dataframes.dataframe import DataFrameType, dataframe
from hopeit.dataframes.dataframeobject import DataFrameObjectType, dataframeobject
from hopeit.dataobjects import DataObject
import numpy as np
import pandas as pd

__all__ = ["dataframe", "dataframeobject"]


class DataFrames(Generic[DataFrameType, DataFrameObjectType, DataObject]):

    @staticmethod
    async def serialize(obj: DataFrameObjectType) -> DataObject:
        return await obj._serialize()  # type: ignore
    
    @staticmethod
    def from_df(datatype: Type[DataFrameType], df: pd.DataFrame, **series: Dict[str, pd.Series]) -> DataFrameType:
        return datatype._from_df(df, **series)  # type: ignore
    
    @staticmethod
    def from_dataframe(datatype: Type[DataFrameType], obj: DataFrameType, **series: Dict[str, pd.Series]) -> DataFrameType:
        return datatype._from_df(obj._df, **series)  # type: ignore
    
    @staticmethod
    def from_dataobjects(datatype: Type[DataFrameType], dataobjects: Iterator[DataFrameObjectType]) -> DataFrameType:
        return datatype._from_dataobjects(dataobjects)  # type: ignore
    
    @staticmethod
    def to_dataobjects(obj: DataFrameObjectType) -> List[DataFrameObjectType]:
        return obj._to_dataobjects()  # type: ignore
    
    @staticmethod
    def from_array(datatype: Type[DataFrameType], array: np.ndarray) -> DataFrameType:
        return datatype._from_array(array)  # type: ignore

    @staticmethod
    def df(obj: DataFrameType) -> pd.DataFrame:
        return obj._df  # type: ignore
