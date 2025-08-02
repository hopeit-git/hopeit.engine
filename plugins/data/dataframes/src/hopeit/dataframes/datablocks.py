"""
DataBlocks is a utility that allows users of the dataframes plugin to create dataobjects
that contain combined properties with one or multiple Datasets but can be manipulated
and saved as a single flat pandas DataFrame.
"""

from datetime import datetime
from typing import AsyncGenerator, Generic, Optional, Type, TypeVar, get_args, get_origin

# try:
import polars as pl
# except ImportError:
#     import hopeit.dataframes.pandas.pandas_mock as pd  # type: ignore[no-redef]

from hopeit.dataobjects import dataobject, dataclass, fields

from hopeit.dataframes.serialization.dataset import Dataset, DatasetLoadError
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

    def __init__(self, datatype: Type[DataBlockType], df: pl.DataFrame) -> None:
        self.datatype = datatype
        self.df = df

    @classmethod
    def from_dataobjects(
        cls, datatype: Type[DataBlockType], items: list[DataBlockItemType]
    ) -> "TempDataBlock[DataBlockType, DataBlockItemType]":
        result_df: Optional[pl.DataFrame] = None
        for field_name, field_info in fields(datatype).items():  # type: ignore[type-var]
            if get_origin(field_info.annotation) is Dataset:
                block_items = (getattr(item, field_name) for item in items)
                block_type = get_args(field_info.annotation)[0]
                block = block_type._from_dataobjects(block_items)
                block_df = block._df
            else:
                block_df = pl.DataFrame({field_name: [getattr(item, field_name) for item in items]})

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
        schema_validation: bool = True,
        database_key: Optional[str] = None,
    ) -> pl.DataFrame:
        """
        Converts a DataBlockType object to a pandas DataFrame, by reading the subyacent Dataset/s and
        putting al the fields defined in the DataBlockType in a flat pandas DataFrame.

        Args:
            datablock (DataBlockType): The data block to convert.
            select (Optional[list[str]]): Optional list of field names to select.
            database_key (Optional[str]): Optional database key for loading data.

        Returns:
            pl.DataFrame: The resulting pandas DataFrame.
        """
        dataset_types = cls._get_dataset_types(type(datablock), select=select)
        field_names = cls._get_field_names(dataset_types)

        # Load data from first dataset (datablock uses a single file for all datasets)
        dataset: Dataset = getattr(datablock, dataset_types[0][0])
        storage = await get_dataset_storage(database_key)
        result_df = await DataBlocks._load_datablock_df(
            storage, dataset, columns=None, database_key=database_key
        )

        # Enfore datatypes and add missing optional fields using class schema (allows schema evolution)
        if schema_validation:
            cls._adapt_to_schema(dataset_types, result_df)
            result_df = result_df[field_names]

        # Adding constant value fields from serialized datablock
        for field_name, field_info in fields(datablock).items():  # type: ignore[arg-type]
            if get_origin(field_info.annotation) is not Dataset:
                result_df.loc[:, field_name] = getattr(datablock, field_name)  # type: ignore[index]

        return result_df

    @staticmethod
    async def save(
        datatype: Type[DataBlockType],
        df: pl.DataFrame,
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
            df (pl.DataFrame): The pandas DataFrame to convert.
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
    def _get_dataset_types(
        datatype: Type[DataBlockType], *, select: list[str] | None = None
    ) -> list[tuple[str, DataFrameType]]:
        return [
            (field_name, get_args(field_info.annotation)[0])
            for field_name, field_info in fields(datatype).items()  # type: ignore[type-var]
            if get_origin(field_info.annotation) is Dataset
            and (select is None or field_name in select)
        ]

    @staticmethod
    def _get_field_names(dataset_types: list[tuple[str, DataFrameType]]) -> list[str]:
        return list(
            dict.fromkeys(
                [
                    field_name
                    for _, dataset_type in dataset_types
                    for field_name, _ in fields(dataset_type).items()  # type: ignore[arg-type]
                ]
            )
        )

    @staticmethod
    def default(datatype: Type[DataBlockType]) -> DataBlockType:
        return datatype(**{field_name: [] for field_name in list(fields(datatype))})  # type: ignore[type-var]

    @classmethod
    async def load_batch(
        cls,
        datatype: Type[DataBlockType],
        query: DataBlockQuery,
        metadata: DataBlockMetadata | None = None,
        schema_validation: bool = True,
        **kwargs,  # Non-Dataset field values for DataBlockType
    ) -> AsyncGenerator[pl.DataFrame, None]:
        if metadata is None:
            metadata = DataBlockMetadata.default()

        storage = await get_dataset_storage(metadata.database_key)

        dataset_types = cls._get_dataset_types(datatype, select=query.select)
        field_names = cls._get_field_names(dataset_types)

        async for block_dataset in storage._get_batch(  # type: ignore[attr-defined]
            datatype,
            database_key=metadata.database_key,
            from_partition_dt=query.from_partition_dt,
            to_partition_dt=query.to_partition_dt,
            group_key=metadata.group_key,
            collection=metadata.collection,
        ):
            result_df = await DataBlocks._load_datablock_df(
                storage, block_dataset, columns=None, database_key=metadata.database_key
            )

            # Enfore datatypes and add missing optional fields using class schema (allows schema evolution)
            if schema_validation:
                cls._adapt_to_schema(dataset_types, result_df)
                result_df = result_df[field_names]

            # Adding constant value fields from kwargs
            for field_name, field_info in fields(datatype).items():  # type: ignore[type-var]
                if get_origin(field_info.annotation) is not Dataset:
                    result_df.loc[:, field_name] = kwargs.get(field_name)

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
    ) -> pl.DataFrame:
        try:
            return await dataset._load_df(storage, columns)
        except (RuntimeError, IOError, KeyError) as e:
            raise DatasetLoadError(
                f"Error {type(e).__name__}: {e} loading datablock of type {dataset.datatype} "
                f"at location {dataset.partition_key}/{dataset.key}"
            ) from e

    @classmethod
    def _adapt_to_schema(
        cls, dataset_types: list[tuple[str, DataFrameType]], df: pl.DataFrame
    ) -> None:
        for _, datatype in dataset_types:
            valid_df = datatype._from_df(df)._df  # type: ignore[attr-defined]
            for col in valid_df.columns:
                df[col] = valid_df[col]
