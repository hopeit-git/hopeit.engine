"""
DataBlocks is a utility that allows users of the dataframes plugin to create dataobjects
that contain combined properties with one or multiple Datasets but can be manipulated
and saved as a single flat pandas DataFrame.
"""

from datetime import datetime
from typing import AsyncGenerator, Generic, Optional, Type, TypeVar, get_args, get_origin

try:
    import pandas as pd
except ImportError:
    import hopeit.dataframes.pandas.pandas_mock as pd  # type: ignore[no-redef]

from hopeit.dataobjects import dataobject, dataclass, fields

from hopeit.dataframes.serialization.dataset import Dataset, DatasetLoadError
from hopeit.dataframes.serialization.protocol import find_dataframe_type
from hopeit.dataframes.setup.registry import get_dataset_storage

DataBlockType = TypeVar("DataBlockType")
DataBlockItemType = TypeVar("DataBlockItemType")
DataFrameType = TypeVar("DataFrameType")


@dataobject
@dataclass
class DataBlockMetadata:
    partition_dt: Optional[datetime] = None
    database_key: Optional[str] = None
    group_key: Optional[str] = None
    collection: Optional[str] = None

    @classmethod
    def default(cls) -> "DataBlockMetadata":
        return cls()


@dataobject
@dataclass
class DataBlockQuery:
    from_partition_dt: datetime
    to_partition_dt: datetime
    select: list[str] | None = None


class TempDataBlock(Generic[DataBlockType, DataBlockItemType]):
    """
    TempDataBlock allows to convers a pandas Dataframe to a from dataobjects
    using DatabBlockType and DataBlockItemType schemas. So from a flat pandas
    dataframe, an object containing subsections of the data can be created.
    """

    def __init__(self, datatype: Type[DataBlockType], df: pd.DataFrame) -> None:
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
    """
    DataBlocks is a utility class that allows users to create dataobjects containing multiple Datasets.
    These dataobjects can be converted and saved as a single pandas DataFrame.
    """

    @classmethod
    async def load(
        cls,
        datablock: DataBlockType,
        *,
        select: Optional[list[str]] = None,
        database_key: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Converts a DataBlockType object to a pandas DataFrame, by reading the subyacent Dataset/s and
        putting al the fields defined in the DataBlockType in a flat pandas DataFrame.

        Args:
            datablock (DataBlockType): The data block to convert.
            select (Optional[list[str]]): Optional list of field names to select.
            database_key (Optional[str]): Optional database key for loading data.

        Returns:
            pd.DataFrame: The resulting pandas DataFrame.
        """
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
        storage = await get_dataset_storage(database_key)
        result_df = await DataBlocks._load_datablock_df(storage, dataset, field_names, database_key)

        # Enfore datatypes and add missing optional fields using class schema (allows schema evolution)
        cls._adapt_to_schema(datablock, keys, result_df)

        # Adding constant value fields
        for field_name, field_info in fields(datablock).items():  # type: ignore[arg-type]
            if get_origin(field_info.annotation) is not Dataset:
                result_df[field_name] = getattr(datablock, field_name)  # type: ignore[index]

        return result_df

    @staticmethod
    async def save(
        datatype: Type[DataBlockType],
        df: pd.DataFrame,
        metadata: DataBlockMetadata | None = None,
        **kwargs,  # Non-Dataset field values for DataBlockType
    ) -> DataBlockType:
        """
        Creates a DataBlockType object from a pandas DataFrame, by saving the pandas Dataframe to a single
        location, usually a file, and returning a dataobject with Datasets that reference the saved data.
        The returned DataBlock can be retrieved in one shot using `DataBlocks.df` to get back a flat pandas
        DataFrame, or each of the individual DataSets can be loaded independently.

        Args:
            datatype (Type[DataBlockType]): The type of the data block.
            df (pd.DataFrame): The pandas DataFrame to convert.
            metadata (Optional[DataBlockMetadata]): Optional metadata for the data block.
            **kwargs: Additional non-Dataset field values for the DataBlockType.

        Returns:
            DataBlockType: The resulting data block.
        """
        if metadata is None:
            metadata = DataBlockMetadata.default()

        storage = await get_dataset_storage(metadata.database_key)

        block_dataset = await Dataset._save_df(
            storage,
            df,
            datatype,
            database_key=metadata.database_key,
            partition_dt=metadata.partition_dt,
            group_key=metadata.group_key,
            collection=metadata.collection,
            save_schema=True,  # Required for datablocks
        )

        blocks = {}
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

    @classmethod
    async def load_batch(
        cls,
        datatype: Type[DataBlockType],
        query: DataBlockQuery,
        metadata: DataBlockMetadata | None = None,
        **kwargs,  # Non-Dataset field values for DataBlockType
    ) -> AsyncGenerator[pd.DataFrame, None]:
        if metadata is None:
            metadata = DataBlockMetadata.default()

        storage = await get_dataset_storage(metadata.database_key)

        async for block_dataset in storage._get_batch(  # type: ignore[attr-defined]
            datatype,
            database_key=metadata.database_key,
            from_partition_dt=query.from_partition_dt,
            to_partition_dt=query.to_partition_dt,
            group_key=metadata.group_key,
            collection=metadata.collection,
        ):
            dataset_types = [
                (field_name, get_args(field_info.annotation)[0])
                for field_name, field_info in fields(datatype).items()  # type: ignore[type-var]
                if get_origin(field_info.annotation) is Dataset
                and (query.select is None or field_name in query.select)
            ]
            field_names = list(
                dict.fromkeys(
                    [
                        field_name
                        for _, dataset_type in dataset_types
                        for field_name, _ in fields(dataset_type).items()
                    ]
                )
            )
            result_df = await DataBlocks._load_datablock_df(
                storage, block_dataset, field_names, metadata.database_key
            )

            # Adding constant value fields
            for field_name, field_info in fields(datatype).items():  # type: ignore[type-var]
                if get_origin(field_info.annotation) is not Dataset:
                    result_df[field_name] = kwargs.get(field_name)

            yield result_df

    @staticmethod
    def _get_datablock_keys(
        datablocktype: Type[DataBlockType],
        *,
        select: Optional[list[str]] = None,
    ) -> list[str]:
        return [
            field_name
            for field_name, field_info in fields(datablocktype).items()  # type: ignore[type-var]
            if get_origin(field_info.annotation) is Dataset
            and (select is None or field_name in select)
        ]

    @staticmethod
    async def _load_datablock_df(
        storage: object,
        dataset: Dataset,
        columns: Optional[list[str]] = None,
        database_key: Optional[str] = None,
    ) -> pd.DataFrame:
        try:
            return await dataset._load_df(storage, columns)
        except (RuntimeError, IOError, KeyError) as e:
            raise DatasetLoadError(
                f"Error {type(e).__name__}: {e} loading datablock of type {dataset.datatype} "
                f"at location {dataset.partition_key}/{dataset.key}"
            ) from e

    @classmethod
    def _adapt_to_schema(cls, datablock: DataBlockType, keys: list[str], df: pd.DataFrame) -> None:
        for key in keys:
            datatype = find_dataframe_type(getattr(datablock, key).datatype)  # type: ignore[var-annotated]
            valid_df = datatype._from_df(df)._df
            for col in valid_df.columns:
                df[col] = valid_df[col]
