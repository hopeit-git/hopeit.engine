from typing import Generic, Optional, Type, TypeVar, get_args, get_origin

import pandas as pd
from hopeit.dataobjects import fields

from hopeit.dataframes.serialization.dataset import Dataset, DatasetLoadError, find_dataframe_type

DataBlockType = TypeVar("DataBlockType")
DataBlockItemType = TypeVar("DataBlockItemType")
DataFrameType = TypeVar("DataFrameType")


class TempDataBlock(Generic[DataBlockType, DataBlockItemType]):
    def __init__(self, datatype: Type[DataBlockType], df: pd.DataFrame):
        self.datatype = datatype
        self.df = df

    @classmethod
    def from_dataobjects(
        cls, datatype: Type[DataBlockType], items: list[DataBlockItemType]
    ) -> "TempDataBlock[DataBlockType, DataBlockItemType]":
        result_df: Optional[pd.DataFrame] = None
        for field_name, field_info in fields(datatype).items():  # type: ignore[type-var]
            if get_origin(field_info.annotation) is Dataset:
                block_items = (getattr(item, field_name) for item in items)
                block_type = get_args(field_info.annotation)[0]
                block = block_type._from_dataobjects(block_items)
                block_df = block._df
            else:
                block_df = pd.DataFrame({field_name: [getattr(item, field_name) for item in items]})

            if result_df is None:
                result_df = block_df
            else:
                # Skips duplicated column names to they are included only once
                result_df = result_df.join(
                    block_df[[col for col in block_df.columns if col not in result_df.columns]]
                )
        assert result_df is not None
        return cls(datatype, result_df)

    def to_dataobjects(
        self, item_type: Type[DataBlockItemType], *, normalize_null_values: bool = False
    ) -> list[DataBlockItemType]:
        keys: list[str] = []
        entries: list[list] = []
        for field_name, field_info in fields(self.datatype).items():  # type: ignore[type-var]
            if get_origin(field_info.annotation) is Dataset:
                block_type = get_args(field_info.annotation)[0]
                keys.append(field_name)
                dataframe = block_type._from_df(self.df)
                entries.append(
                    dataframe._to_dataobjects(normalize_null_values=normalize_null_values)
                )
            else:
                keys.append(field_name)
                entries.append(self.df[field_name].to_list())

        return [
            item_type(**{field_name: entry[i] for i, field_name in enumerate(keys)})
            for entry in zip(*entries)
        ]


class DataBlocks(Generic[DataBlockType, DataFrameType]):
    @classmethod
    async def df(cls, datablock: DataBlockType, select: Optional[list[str]] = None) -> pd.DataFrame:
        keys = [
            field_name
            for field_name, field_info in fields(datablock).items()  # type: ignore[arg-type]
            if get_origin(field_info.annotation) is Dataset
            and (select is None or field_name in select)
        ]

        # Filter/validate selected field names using saved schema,
        # generates a single field for every common/duplicated field in the datasets
        field_names = list(
            dict.fromkeys(
                [
                    field_name
                    for key in keys
                    for field_name in getattr(datablock, key).schema["properties"].keys()
                ]
            )
        )

        # Load data from first dataset (datablock uses a single file for all datasets)
        dataset: Dataset = getattr(datablock, keys[0])
        result_df = await DataBlocks._load_datablock_df(dataset, field_names)

        # Add missing optional fields using class schema (allows schema evolution)
        cls._adapt_to_schema(datablock, keys, result_df)

        # Adding constant value fields
        for field_name, field_info in fields(datablock).items():  # type: ignore[arg-type]
            if get_origin(field_info.annotation) is not Dataset:
                result_df[field_name] = getattr(datablock, field_name)  # type: ignore[index]

        return result_df

    @staticmethod
    async def from_df(
        datatype: Type[DataBlockType],
        df: pd.DataFrame,
        **kwargs,  # Non-Dataset field values for DataBlockType
    ) -> DataBlockType:
        blocks = {}
        block_dataset = await Dataset._save_df(df, datatype)
        for field_name, field_info in fields(datatype).items():  # type: ignore[type-var]
            if get_origin(field_info.annotation) is Dataset:
                block_type = get_args(field_info.annotation)[0]
                blocks[field_name] = block_dataset._adapt(block_type)
            else:
                blocks[field_name] = kwargs[field_name]

        return datatype(**blocks)

    @staticmethod
    def default(datatype: Type[DataBlockType]) -> DataBlockType:
        return datatype(**{field_name: [] for field_name in list(fields(datatype))})  # type: ignore[type-var]

    @staticmethod
    async def _load_datablock_df(
        dataset: Dataset, columns: Optional[list[str]] = None
    ) -> pd.DataFrame:
        try:
            return await dataset._load_df(columns)
        except (RuntimeError, IOError, KeyError) as e:
            raise DatasetLoadError(
                f"Error {type(e).__name__}: {e} loading datablock of type {dataset.datatype} "
                f"at location {dataset.partition_key}/{dataset.key}"
            ) from e

    @classmethod
    def _adapt_to_schema(cls, datablock: DataBlockType, keys: list[str], df: pd.DataFrame):
        for key in keys:
            datatype = find_dataframe_type(getattr(datablock, key).datatype)  # type: ignore[var-annotated]
            valid_df = datatype._from_df(df)._df
            for col in valid_df.columns:
                df[col] = valid_df[col]
