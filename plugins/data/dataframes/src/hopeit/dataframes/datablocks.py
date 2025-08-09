"""
DataBlocks is a utility that allows users of the dataframes plugin to create dataobjects
that contain combined properties with one or multiple Datasets but can be manipulated
and saved as a single flat polars DataFrame.
"""

from datetime import datetime
from types import NoneType
from typing import (
    Any,
    AsyncGenerator,
    Generic,
    Optional,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
)

try:
    import polars as pl
except ImportError:
    import hopeit.dataframes.polars as pl  # type: ignore  # Polars is optional; set to a mock if not installed

from hopeit.dataframes.dataframe import DataTypeMapping
from hopeit.dataobjects import dataobject, dataclass, fields

from hopeit.dataframes.serialization.dataset import Dataset, DatasetLoadError
from hopeit.dataframes.setup.registry import get_dataset_storage

DataBlockType = TypeVar("DataBlockType")
DataBlockItemType = TypeVar("DataBlockItemType")
DataFrameType = TypeVar("DataFrameType")
PolarsDataFrameT = TypeVar("PolarsDataFrameT", bound=Union[pl.DataFrame, pl.LazyFrame])


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


def get_datablock_schema(cls: Type[DataBlockType], *, datasets_only: bool = False) -> pl.Schema:
    schema_fields: dict[str, pl.DataType] = {}
    for block_field, block_info in fields(cls).items():  # type: ignore[type-var]
        if get_origin(block_info.annotation) is Dataset:
            block_type = get_args(block_info.annotation)[0]
            for field_name, field_info in fields(block_type).items():  # type: ignore[type-var]
                datatype = DataTypeMapping.get_schema_type(field_info.annotation)  # type: ignore[arg-type]
                if datatype is None:
                    raise TypeError(
                        f"{cls.__name__}: Unsupported type for field {field_name}: {field_info.annotation}"
                    )
                schema_fields[field_name] = datatype
        elif not datasets_only:
            datatype = DataTypeMapping.get_schema_type(block_info.annotation)  # type: ignore[arg-type]
            if datatype is None:
                raise TypeError(
                    f"{cls.__name__}: Unsupported type for field {block_field}: {block_info.annotation}"
                )
            schema_fields[block_field] = datatype

    return pl.Schema(schema_fields)


class TempDataBlock(Generic[DataBlockType, DataBlockItemType]):
    """
    TempDataBlock allows to convers a polars Dataframe to a from dataobjects
    using DatabBlockType and DataBlockItemType schemas. So from a flat polars
    dataframe, an object containing subsections of the data can be created.
    """

    def __init__(self, datatype: Type[DataBlockType], df: pl.DataFrame) -> None:
        self.datatype = datatype
        self.df = df

    @classmethod
    def from_dataobjects(
        cls, datatype: Type[DataBlockType], items: list[DataBlockItemType], *, strict=True
    ) -> "TempDataBlock[DataBlockType, DataBlockItemType]":
        schema = get_datablock_schema(datatype)
        result_df = pl.DataFrame(schema=schema)
        if len(items) == 0:
            return cls(datatype, result_df)
        for field_name, field_info in fields(datatype).items():  # type: ignore[type-var]
            if get_origin(field_info.annotation) is Dataset:
                block_items = (getattr(item, field_name) for item in items)
                block_type = get_args(field_info.annotation)[0]
                block = block_type._from_dataobjects(block_items)
                new_series = [series for series in block._df]
            else:
                new_series = [
                    pl.Series(
                        name=field_name,
                        values=[getattr(item, field_name) for item in items],
                        dtype=schema.get(field_name),
                    )
                ]

            if len(result_df) == 0:
                result_df = pl.DataFrame(new_series)
            else:
                result_df = result_df.with_columns([series for series in new_series])

        if strict and result_df.schema != schema:
            raise TypeError(
                f"{datatype.__name__}: Schema mismatch. Use `strict=False` to create TempDataBlock anyway."
            )

        return cls(datatype, result_df)

    def to_dataobjects(
        self,
        item_type: Type[DataBlockItemType],
    ) -> list[DataBlockItemType]:
        keys: list[str] = []
        entries: list[list] = []
        for field_name, field_info in fields(self.datatype).items():  # type: ignore[type-var]
            if get_origin(field_info.annotation) is Dataset:
                block_type = get_args(field_info.annotation)[0]
                keys.append(field_name)
                dataframe = block_type._from_df(self.df)
                entries.append(dataframe._to_dataobjects())
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
    These dataobjects can be converted and saved as a single polars DataFrame.
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
        Converts a DataBlockType object to a polars DataFrame, by reading the subyacent Dataset/s and
        putting the fields defined in the DataBlockType in a flat polars DataFrame.

        Args:
            datablock (DataBlockType): The data block to convert.
            select (Optional[list[str]]): Optional list of field names to select.
            database_key (Optional[str]): Optional database key for loading data.

        Returns:
            pl.DataFrame: The resulting polars DataFrame.
        """
        dataset_types = cls._get_dataset_types(type(datablock), select=select)
        field_names = cls._get_field_names(dataset_types)

        # Load data from first dataset (datablock uses a single file for all datasets)
        dataset: Dataset = getattr(datablock, dataset_types[0][0])
        storage = await get_dataset_storage(database_key)
        result_df = await DataBlocks._load_datablock_df(
            storage,
            dataset,
            columns=None,
        )

        # Enfore datatypes and add missing optional fields using class schema (allows schema evolution)
        if schema_validation:
            result_df = cls._adapt_to_schema(result_df, dataset_types, select_cols=field_names)

        # Adding constant value fields from serialized datablock
        return cls._add_datablock_atomic_fields(result_df, datablock, field_names)
        # result_df = result_df.with_columns(
        #     [
        #         pl.lit(getattr(datablock, field_name))
        #         .cast(cls._get_col_type(field_name, field_info.annotation or NoneType))
        #         .alias(field_name)
        #         for field_name, field_info in fields(datablock).items()  # type: ignore[arg-type]
        #         if get_origin(field_info.annotation) is not Dataset
        #     ]
        # )

        # return result_df

    @classmethod
    async def scan(
        cls,
        datablock: DataBlockType,
        *,
        select: Optional[list[str]] = None,
        schema_validation: bool = True,
        database_key: Optional[str] = None,
    ) -> pl.LazyFrame:
        """
        Converts a DataBlockType object to a polars LazyFrame, by reading the subyacent Dataset/s and
        putting the fields defined in the DataBlockType in a flat polars LazyFrame.

        NOTE: Reading of data relies on polars scan_parquet which is not async.
        Use `polars.LazyFrame.collect_async()` to perform a non-blocking read, or
        use `DataBlocks.load` to read data using async I/O, with the caveat that it won't be lazy.

        Args:
            datablock (DataBlockType): The data block to convert.
            select (Optional[list[str]]): Optional list of field names to select.
            database_key (Optional[str]): Optional database key for loading data.

        Returns:
            pl.DataFrame: The resulting polars DataFrame.
        """
        schema = (
            get_datablock_schema(type(datablock), datasets_only=True) if schema_validation else None
        )

        # Load data from first dataset (datablock uses a single file for all datasets)
        dataset_types = cls._get_dataset_types(type(datablock), select=select)
        dataset: Dataset = getattr(datablock, dataset_types[0][0])
        storage = await get_dataset_storage(database_key)
        result_df = DataBlocks._scan_datablock_df(
            storage,
            dataset,
            schema=schema,
        )

        # Lazily selecting field and adding constant value fields from serialized datablock
        return cls._add_datablock_atomic_fields(
            result_df, datablock, cls._get_field_names(dataset_types)
        )

    @classmethod
    def _add_datablock_atomic_fields(
        cls, df: PolarsDataFrameT, datablock: DataBlockType, field_names: list[str]
    ) -> PolarsDataFrameT:
        return df.select(  # type: ignore[return-value]
            [pl.col(field_name) for field_name in field_names]
        ).with_columns(
            [
                pl.lit(getattr(datablock, field_name))
                .cast(cls._get_col_type(field_name, field_info.annotation or NoneType))
                .alias(field_name)
                for field_name, field_info in fields(datablock).items()  # type: ignore[arg-type]
                if get_origin(field_info.annotation) is not Dataset
            ]
        )

    @staticmethod
    def _get_col_type(field_name: str, annotation: type):
        typedef = DataTypeMapping.get_schema_type(annotation)
        if typedef is None:
            raise TypeError(f"Datablocks: unsupported field type: {field_name}: {annotation}")
        return typedef

    @classmethod
    async def save(
        cls,
        datatype: Type[DataBlockType],
        df: pl.DataFrame,
        metadata: DataBlockMetadata | None = None,
        enforce_schema: bool = True,
        **kwargs,  # Non-Dataset field values for DataBlockType
    ) -> DataBlockType:
        """
        Creates a DataBlockType object from a polars DataFrame, by saving the polars Dataframe to a single
        location, usually a file, and returning a dataobject with Datasets that reference the saved data.
        The returned DataBlock can be retrieved in one shot using `DataBlocks.df` to get back a flat polars
        DataFrame, or each of the individual DataSets can be loaded independently.

        Args:
            datatype (Type[DataBlockType]): The type of the data block.
            df (pl.DataFrame): The polars DataFrame to convert.
            metadata (Optional[DataBlockMetadata]): Optional metadata for the data block.
            **kwargs: Additional non-Dataset field values for the DataBlockType.

        Returns:
            DataBlockType: The resulting data block.
        """
        if metadata is None:
            metadata = DataBlockMetadata.default()

        storage = await get_dataset_storage(metadata.database_key)
        dataset_types = cls._get_dataset_types(datatype)
        field_names = cls._get_field_names(dataset_types)

        # Enfore datatypes and add missing optional fields using class schema
        # so this dataframe can be lazily loaded with DataBlocks.scan that does not support schema
        # evolution on read
        if enforce_schema:
            df = df.cast(get_datablock_schema(datatype, datasets_only=True))  # type: ignore[arg-type]
            df = cls._adapt_to_schema(df, dataset_types, select_cols=field_names)

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
            elif field_name in kwargs:
                blocks[field_name] = kwargs[field_name]

        return datatype(**blocks)

    @staticmethod
    async def sink_partitions(
        datatype: Type[DataBlockType],
        df: pl.LazyFrame,
        partition_by: list[str],
        partition_interval: str = "1d",
        metadata: DataBlockMetadata | None = None,
        **kwargs,  # Non-Dataset field values for DataBlockType
    ) -> AsyncGenerator[DataBlockType, None]:
        """
        Saves DataBlockType objects from a polars DataFrame, by saving the polars Dataframe to multiple files
        partitioned by the specified datetime fields, and using the provided time unit.
        This method yields dataobjects with Datasets that reference the saved data.
        The returned DataBlocks can be retrieved later with `DataBlocks.load_batch` or `DataBlocks.query`
        in order to iterate over the created partitions.
        Args:
            datatype (Type[DataBlockType]): The type of the data block.
            df (pl.LazyFrame): The polars LazyFrame to convert.
            metadata (Optional[DataBlockMetadata]): Optional metadata for the data block.
            partition_by: list of fields used for partitioning.
            partition_interval: for datetime fields specified in partition_by, they will be truncated to this time unit.
                (Default: "1d" = 1 day)
            **kwargs: Additional non-Dataset field values for the DataBlockType.

        Returns:
            DataBlockType: yields the resulting data blocks.
        """
        if metadata is None:
            metadata = DataBlockMetadata.default()

        schema = get_datablock_schema(datatype)

        eff_partition_fields = []
        partition_dt_index = -1
        for i, partition_field in enumerate(partition_by):
            if isinstance(schema.get(partition_field), pl.Datetime):
                field_name = f"partition_{partition_field}"
                df = df.with_columns(
                    [pl.col(partition_field).dt.truncate(partition_interval).alias(field_name)]
                )
                eff_partition_fields.append(field_name)
                partition_dt_index = i
            else:
                eff_partition_fields.append(partition_field)

        partition_keys = (
            await df.select([pl.col(field_name) for field_name in eff_partition_fields])
            .unique(subset=eff_partition_fields)
            .collect_async()
        )

        for keys in partition_keys.rows():
            part_df = df.filter(
                [
                    pl.col(field_name) == value
                    for field_name, value in zip(eff_partition_fields, keys)
                ]
            )

            part_metatada = DataBlockMetadata(
                partition_dt=metadata.partition_dt
                if partition_dt_index < 0
                else keys[partition_dt_index],
                database_key=metadata.database_key,
                group_key=metadata.group_key,
                collection=metadata.collection,
            )
            datablock = await DataBlocks.save(
                datatype,
                await part_df.collect_async(),
                part_metatada,
                # Add generated partition fields if any
                **{
                    **{
                        field_name: value
                        for field_name, value in zip(eff_partition_fields, keys)
                        if field_name not in partition_by
                    },
                    **kwargs,
                },
            )
            yield datablock

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
    async def query(
        cls,
        datatype: Type[DataBlockType],
        query: DataBlockQuery,
        metadata: DataBlockMetadata | None = None,
        schema_validation: bool = True,
        # **kwargs,  # Non-Dataset field values for DataBlockType
    ) -> pl.LazyFrame:
        if metadata is None:
            metadata = DataBlockMetadata.default()

        schema = get_datablock_schema(datatype, datasets_only=True)
        storage = await get_dataset_storage(metadata.database_key)

        if query.select:
            dataset_types = cls._get_dataset_types(datatype, select=query.select)
            field_names = cls._get_field_names(dataset_types)
        else:
            field_names = schema.names()

        frames: list[pl.LazyFrame] = []

        async for block_dataset in storage._get_batch(  # type: ignore[attr-defined]
            datatype,
            database_key=metadata.database_key,
            from_partition_dt=query.from_partition_dt,
            to_partition_dt=query.to_partition_dt,
            group_key=metadata.group_key,
            collection=metadata.collection,
        ):
            frames.append(
                cls._scan_datablock_df(
                    storage,
                    block_dataset,
                    schema=schema if schema_validation else None,
                ).select(field_names)
            )

        if len(frames) == 0:
            return pl.DataFrame(schema=schema).lazy()

        return pl.concat(frames)

    @classmethod
    async def load_batch(
        cls,
        datatype: Type[DataBlockType],
        query: DataBlockQuery,
        metadata: DataBlockMetadata | None = None,
        schema_validation: bool = True,
        # **kwargs,  # Non-Dataset field values for DataBlockType
    ) -> AsyncGenerator[pl.DataFrame, None]:
        if metadata is None:
            metadata = DataBlockMetadata.default()

        storage = await get_dataset_storage(metadata.database_key)
        schema = get_datablock_schema(datatype, datasets_only=True)

        if query.select:
            dataset_types = cls._get_dataset_types(datatype, select=query.select)
            field_names = cls._get_field_names(dataset_types)
        else:
            field_names = schema.names()

        async for block_dataset in storage._get_batch(  # type: ignore[attr-defined]
            datatype,
            database_key=metadata.database_key,
            from_partition_dt=query.from_partition_dt,
            to_partition_dt=query.to_partition_dt,
            group_key=metadata.group_key,
            collection=metadata.collection,
        ):
            result_df = await cls._load_datablock_df(
                storage,
                block_dataset,
                columns=None,
            )

            # Enfore datatypes and add missing optional fields using class schema (allows schema evolution)
            if schema_validation:
                result_df = result_df.cast(schema)  # type: ignore[arg-type]

            yield result_df.select(field_names)

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
    ) -> pl.DataFrame:
        try:
            return await dataset._load_df(storage, columns)
        except (RuntimeError, IOError, KeyError) as e:
            raise DatasetLoadError(
                f"Error {type(e).__name__}: {e} loading datablock of type {dataset.datatype} "
                f"at location {dataset.partition_key}/{dataset.key}"
            ) from e

    @staticmethod
    def _scan_datablock_df(
        storage: object,
        dataset: Dataset,
        schema: Optional[pl.Schema] = None,
    ) -> pl.LazyFrame:
        try:
            return dataset._scan_df(storage, schema=schema)
        except (RuntimeError, IOError, KeyError) as e:
            raise DatasetLoadError(
                f"Error {type(e).__name__}: {e} loading datablock of type {dataset.datatype} "
                f"at location {dataset.partition_key}/{dataset.key}"
            ) from e

    @staticmethod
    def _adapt_to_schema(
        df: pl.DataFrame,
        dataset_types: list[tuple[str, DataFrameType]],
        select_cols: list[str],
    ) -> pl.DataFrame:
        datasets: dict[str, pl.DataFrame] = {}
        for dataset_name, datatype in dataset_types:
            schema: pl.Schema = datatype.__dataframe__.schema  # type: ignore[attr-defined]
            for field_name in schema.names():
                if (field_name in select_cols) and (field_name not in df.columns):
                    dataset_df = datasets.get(dataset_name)
                    if dataset_df is None:
                        dataset_df = datatype._from_df(df)._df  # type: ignore[attr-defined]
                        datasets[dataset_name] = dataset_df

                    df = df.with_columns(dataset_df[field_name])
        return df.select([pl.col(field_name) for field_name in select_cols])

    @staticmethod
    def schema(datablocktype: Type[DataBlockType]) -> pl.Schema:
        return get_datablock_schema(datablocktype)

    @staticmethod
    def to_pandas(datablocktype: type[DataBlockType], df: pl.DataFrame) -> "Any":
        return df.cast(get_datablock_schema(datablocktype)).to_pandas()  # type: ignore[arg-type]

    @staticmethod
    def from_pandas(datablocktype: type[DataBlockType], pandas_df: "Any") -> pl.DataFrame:
        return pl.from_pandas(pandas_df, schema_overrides=get_datablock_schema(datablocktype))
