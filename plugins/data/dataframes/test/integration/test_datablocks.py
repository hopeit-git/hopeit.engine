from datetime import datetime, timezone
import os
from typing import cast
from hopeit.dataframes.datablocks import TempDataBlock
import numpy as np
import polars as pl
from polars.testing import assert_frame_equal

from hopeit.dataframes import DataBlocks, Dataset
from hopeit.dataframes.datablocks import DataBlockMetadata
import pytest

from conftest import (
    MyDataBlock,
    MyDataBlockCompat,
    MyDataBlockItem,
    MyDataBlockNoCompat,
    Part1,
    Part2,
    Part2Compat,
    get_saved_file_path,
    setup_serialization_context,
)


async def test_datablock_creation_and_load(plugin_config, datablock_df) -> None:
    await setup_serialization_context(plugin_config)

    datablock = await DataBlocks.save(MyDataBlock, datablock_df, block_id="b1", block_field=42)

    assert datablock == MyDataBlock(
        block_id="b1",
        block_field=42,
        part1=Dataset(
            protocol="hopeit.dataframes.serialization.files.DatasetFileStorage",
            partition_key=datablock.part1.partition_key,
            key=datablock.part1.key,
            datatype="conftest.Part1",
            collection="mydatablock",
            schema={
                "properties": {
                    "field0": {"title": "Field0", "type": "string"},
                    "field1": {"title": "Field1", "type": "string"},
                    "field2": {"title": "Field2", "type": "number"},
                },
                "required": ["field0", "field1", "field2"],
                "title": "Part1",
                "type": "object",
            },
        ),
        part2=Dataset(
            protocol="hopeit.dataframes.serialization.files.DatasetFileStorage",
            partition_key=datablock.part1.partition_key,
            key=datablock.part1.key,
            datatype="conftest.Part2",
            collection="mydatablock",
            schema={
                "properties": {
                    "field0": {"title": "Field0", "type": "string"},
                    "field3": {"title": "Field3", "type": "string"},
                    "field4": {"title": "Field4", "type": "number"},
                    "field5_opt": {
                        "anyOf": [{"type": "number"}, {"type": "null"}],
                        "default": None,
                        "title": "Field5 Opt",
                    },
                },
                "required": ["field0", "field3", "field4"],
                "title": "Part2",
                "type": "object",
            },
        ),
    )

    # Check single file is created
    saved_location = get_saved_file_path(plugin_config, datablock.part1)
    assert os.path.exists(saved_location)
    assert get_saved_file_path(plugin_config, datablock.part2) == saved_location

    # test get dataframe
    loaded_df = await DataBlocks.load(datablock)

    assert_frame_equal(
        datablock_df.select(
            [
                "field0",
                "field1",
                "field2",
                "field3",
                "field4",
                "field5_opt",
                "block_id",
                "block_field",
            ]
        ),
        loaded_df,
    )

    # test get dataframe
    loaded_df = await DataBlocks.load(datablock, select=["part1"])

    assert_frame_equal(
        datablock_df.select(["field0", "field1", "field2", "block_id", "block_field"]),
        loaded_df,
    )

    # test get dataframe
    loaded_df = await DataBlocks.load(datablock, select=["part2"])

    assert_frame_equal(
        datablock_df.select(
            ["field0", "field3", "field4", "field5_opt", "block_id", "block_field"]
        ),
        loaded_df,
    )


async def test_datablock_custom_database(plugin_config, datablock_df) -> None:
    await setup_serialization_context(plugin_config)

    datablock = await DataBlocks.save(
        MyDataBlock,
        datablock_df,
        DataBlockMetadata(database_key="test_db"),
        block_id="b1",
        block_field=42,
    )

    assert datablock == MyDataBlock(
        block_id="b1",
        block_field=42,
        part1=Dataset(
            protocol="hopeit.dataframes.serialization.files.DatasetFileStorage",
            partition_key=datablock.part1.partition_key,
            key=datablock.part1.key,
            datatype="conftest.Part1",
            database_key="test_db",
            collection="mydatablock",
            schema={
                "properties": {
                    "field0": {"title": "Field0", "type": "string"},
                    "field1": {"title": "Field1", "type": "string"},
                    "field2": {"title": "Field2", "type": "number"},
                },
                "required": ["field0", "field1", "field2"],
                "title": "Part1",
                "type": "object",
            },
        ),
        part2=Dataset(
            protocol="hopeit.dataframes.serialization.files.DatasetFileStorage",
            partition_key=datablock.part1.partition_key,
            key=datablock.part1.key,
            datatype="conftest.Part2",
            database_key="test_db",
            collection="mydatablock",
            schema={
                "properties": {
                    "field0": {"title": "Field0", "type": "string"},
                    "field3": {"title": "Field3", "type": "string"},
                    "field4": {"title": "Field4", "type": "number"},
                    "field5_opt": {
                        "anyOf": [{"type": "number"}, {"type": "null"}],
                        "default": None,
                        "title": "Field5 Opt",
                    },
                },
                "required": ["field0", "field3", "field4"],
                "title": "Part2",
                "type": "object",
            },
        ),
    )

    # Check single file is created
    saved_location = get_saved_file_path(plugin_config, datablock.part1)
    assert os.path.exists(saved_location)
    assert get_saved_file_path(plugin_config, datablock.part2) == saved_location

    # test get dataframe
    loaded_df = await DataBlocks.load(datablock, database_key="test_db")

    assert_frame_equal(
        datablock_df[
            [
                "field0",
                "field1",
                "field2",
                "field3",
                "field4",
                "field5_opt",
                "block_id",
                "block_field",
            ]
        ],
        loaded_df,
    )


async def test_datablock_custom_partition_date(plugin_config, datablock_df) -> None:
    await setup_serialization_context(plugin_config)

    datablock = await DataBlocks.save(
        MyDataBlock,
        datablock_df,
        DataBlockMetadata(
            database_key="test_db", partition_dt=datetime(2024, 1, 1, tzinfo=timezone.utc)
        ),
        block_id="b1",
        block_field=42,
    )

    assert datablock == MyDataBlock(
        block_id="b1",
        block_field=42,
        part1=Dataset(
            protocol="hopeit.dataframes.serialization.files.DatasetFileStorage",
            partition_key="2024/01/01/00/",
            key=datablock.part1.key,
            datatype="conftest.Part1",
            partition_dt=datetime(2024, 1, 1, tzinfo=timezone.utc),
            database_key="test_db",
            collection="mydatablock",
            schema={
                "properties": {
                    "field0": {"title": "Field0", "type": "string"},
                    "field1": {"title": "Field1", "type": "string"},
                    "field2": {"title": "Field2", "type": "number"},
                },
                "required": ["field0", "field1", "field2"],
                "title": "Part1",
                "type": "object",
            },
        ),
        part2=Dataset(
            protocol="hopeit.dataframes.serialization.files.DatasetFileStorage",
            partition_key="2024/01/01/00/",
            key=datablock.part1.key,
            datatype="conftest.Part2",
            partition_dt=datetime(2024, 1, 1, tzinfo=timezone.utc),
            database_key="test_db",
            collection="mydatablock",
            schema={
                "properties": {
                    "field0": {"title": "Field0", "type": "string"},
                    "field3": {"title": "Field3", "type": "string"},
                    "field4": {"title": "Field4", "type": "number"},
                    "field5_opt": {
                        "anyOf": [{"type": "number"}, {"type": "null"}],
                        "default": None,
                        "title": "Field5 Opt",
                    },
                },
                "required": ["field0", "field3", "field4"],
                "title": "Part2",
                "type": "object",
            },
        ),
    )

    # Check single file is created
    saved_location = get_saved_file_path(plugin_config, datablock.part1)
    assert "2024/01/01/00/" in saved_location.as_posix()
    assert os.path.exists(saved_location)
    assert get_saved_file_path(plugin_config, datablock.part2) == saved_location

    # test get dataframe
    loaded_df = await DataBlocks.load(datablock, database_key="test_db")

    assert_frame_equal(
        datablock_df[
            [
                "field0",
                "field1",
                "field2",
                "field3",
                "field4",
                "field5_opt",
                "block_id",
                "block_field",
            ]
        ],
        loaded_df,
    )


async def test_datablock_custom_group(plugin_config, datablock_df) -> None:
    await setup_serialization_context(plugin_config)

    datablock = await DataBlocks.save(
        MyDataBlock,
        datablock_df,
        DataBlockMetadata(
            database_key="test_db",
            group_key="datablock/test_group",
        ),
        block_id="b1",
        block_field=42,
    )

    assert datablock == MyDataBlock(
        block_id="b1",
        block_field=42,
        part1=Dataset(
            protocol="hopeit.dataframes.serialization.files.DatasetFileStorage",
            partition_key=datablock.part1.partition_key,
            key=datablock.part1.key,
            datatype="conftest.Part1",
            database_key="test_db",
            group_key="datablock/test_group",
            collection="mydatablock",
            schema={
                "properties": {
                    "field0": {"title": "Field0", "type": "string"},
                    "field1": {"title": "Field1", "type": "string"},
                    "field2": {"title": "Field2", "type": "number"},
                },
                "required": ["field0", "field1", "field2"],
                "title": "Part1",
                "type": "object",
            },
        ),
        part2=Dataset(
            protocol="hopeit.dataframes.serialization.files.DatasetFileStorage",
            partition_key=datablock.part1.partition_key,
            key=datablock.part1.key,
            datatype="conftest.Part2",
            database_key="test_db",
            group_key="datablock/test_group",
            collection="mydatablock",
            schema={
                "properties": {
                    "field0": {"title": "Field0", "type": "string"},
                    "field3": {"title": "Field3", "type": "string"},
                    "field4": {"title": "Field4", "type": "number"},
                    "field5_opt": {
                        "anyOf": [{"type": "number"}, {"type": "null"}],
                        "default": None,
                        "title": "Field5 Opt",
                    },
                },
                "required": ["field0", "field3", "field4"],
                "title": "Part2",
                "type": "object",
            },
        ),
    )

    # Check single file is created
    saved_location = get_saved_file_path(plugin_config, datablock.part1)
    assert os.path.exists(saved_location)
    assert get_saved_file_path(plugin_config, datablock.part2) == saved_location

    # test get dataframe
    loaded_df = await DataBlocks.load(datablock, database_key="test_db")

    assert_frame_equal(
        datablock_df[
            [
                "field0",
                "field1",
                "field2",
                "field3",
                "field4",
                "field5_opt",
                "block_id",
                "block_field",
            ]
        ],
        loaded_df,
    )


async def test_datablock_custom_collection(plugin_config, datablock_df) -> None:
    await setup_serialization_context(plugin_config)

    datablock = await DataBlocks.save(
        MyDataBlock,
        datablock_df,
        DataBlockMetadata(
            database_key="test_db",
            group_key="datablock/test_group",
            collection="mycollection",
        ),
        block_id="b1",
        block_field=42,
    )

    assert datablock == MyDataBlock(
        block_id="b1",
        block_field=42,
        part1=Dataset(
            protocol="hopeit.dataframes.serialization.files.DatasetFileStorage",
            partition_key=datablock.part1.partition_key,
            key=datablock.part1.key,
            datatype="conftest.Part1",
            database_key="test_db",
            group_key="datablock/test_group",
            collection="mycollection",
            schema={
                "properties": {
                    "field0": {"title": "Field0", "type": "string"},
                    "field1": {"title": "Field1", "type": "string"},
                    "field2": {"title": "Field2", "type": "number"},
                },
                "required": ["field0", "field1", "field2"],
                "title": "Part1",
                "type": "object",
            },
        ),
        part2=Dataset(
            protocol="hopeit.dataframes.serialization.files.DatasetFileStorage",
            partition_key=datablock.part1.partition_key,
            key=datablock.part1.key,
            datatype="conftest.Part2",
            database_key="test_db",
            group_key="datablock/test_group",
            collection="mycollection",
            schema={
                "properties": {
                    "field0": {"title": "Field0", "type": "string"},
                    "field3": {"title": "Field3", "type": "string"},
                    "field4": {"title": "Field4", "type": "number"},
                    "field5_opt": {
                        "anyOf": [{"type": "number"}, {"type": "null"}],
                        "default": None,
                        "title": "Field5 Opt",
                    },
                },
                "required": ["field0", "field3", "field4"],
                "title": "Part2",
                "type": "object",
            },
        ),
    )

    # Check single file is created
    saved_location = get_saved_file_path(plugin_config, datablock.part1)
    assert os.path.exists(saved_location)
    assert get_saved_file_path(plugin_config, datablock.part2) == saved_location

    # test get dataframe
    loaded_df = await DataBlocks.load(datablock, database_key="test_db")

    assert_frame_equal(
        datablock_df[
            [
                "field0",
                "field1",
                "field2",
                "field3",
                "field4",
                "field5_opt",
                "block_id",
                "block_field",
            ]
        ],
        loaded_df,
    )


async def test_tempdatablock(datablock_df) -> None:
    temp_datablock: TempDataBlock[MyDataBlock, MyDataBlockItem] = TempDataBlock(
        MyDataBlock, datablock_df
    )
    dataobjects = temp_datablock.to_dataobjects(MyDataBlockItem, normalize_null_values=True)

    assert dataobjects == [
        MyDataBlockItem(
            block_id="b1",
            block_field=42,
            part1=Part1.DataObject(field0="item1", field1="f11", field2=2.1),  # type: ignore[attr-defined]
            part2=Part2.DataObject(field0="item1", field3="f31", field4=4.1, field5_opt=5.1),  # type: ignore[attr-defined]
        ),
        MyDataBlockItem(
            block_id="b1",
            block_field=42,
            part1=Part1.DataObject(field0="item2", field1="f12", field2=2.2),  # type: ignore[attr-defined]
            part2=Part2.DataObject(field0="item2", field3="f32", field4=4.2, field5_opt=None),  # type: ignore[attr-defined]
        ),
    ]

    new_datablock = TempDataBlock.from_dataobjects(MyDataBlock, dataobjects)

    assert_frame_equal(
        datablock_df[
            [
                "block_id",
                "block_field",
                "field0",
                "field1",
                "field2",
                "field3",
                "field4",
                "field5_opt",
            ]
        ],
        new_datablock.df,
    )


async def test_schema_evolution_compatible(plugin_config, datablock_df) -> None:
    await setup_serialization_context(plugin_config)

    datablock: MyDataBlock = await DataBlocks.save(
        MyDataBlock, datablock_df, block_id="b1", block_field=42
    )

    # Simulating a change in the schemas
    datablock_compat = MyDataBlockCompat(
        block_id=datablock.block_id,
        block_field=datablock.block_field,
        part1=datablock.part1,
        part2=Dataset(
            protocol=datablock.part2.protocol,
            partition_key=datablock.part2.partition_key,
            collection=datablock.part2.collection,
            key=datablock.part2.key,
            datatype="conftest.Part2Compat",  # This is just to emulate Part2 has a new schema
            schema=datablock.part2.schema,  # It was saved using the old schema
        ),
    )
    # test get dataframe
    loaded_df = await DataBlocks.load(datablock_compat)

    datablock_df["field6_opt"] = np.nan
    datablock_df["field7_opt"] = pl.Series(np.nan, dtype=object)

    assert_frame_equal(
        datablock_df[
            [
                "field0",
                "field1",
                "field2",
                "field3",
                "field4",
                "field5_opt",
                "field6_opt",
                "field7_opt",
                "block_id",
                "block_field",
            ]
        ],
        loaded_df,
    )


async def test_schema_evolution_not_compatible(plugin_config, datablock_df) -> None:
    await setup_serialization_context(plugin_config)

    datablock: MyDataBlock = await DataBlocks.save(
        MyDataBlock, datablock_df, block_id="b1", block_field=42
    )

    # Simulating a change in the schemas
    datablock_not_compat = MyDataBlockNoCompat(
        block_id=datablock.block_id,
        block_field=datablock.block_field,
        part1=Dataset(
            protocol=datablock.part1.protocol,
            partition_key=datablock.part1.partition_key,
            collection=datablock.part2.collection,
            key=datablock.part1.key,
            datatype="conftest.Part1NoCompat",  # This is just to emulate Part1 has a new schema
            schema=datablock.part1.schema,  # It was saved using the old schema
        ),
        part2=cast(Dataset[Part2Compat], datablock.part2),
    )

    with pytest.raises(KeyError):
        await DataBlocks.load(datablock_not_compat)


async def test_schema_evolution_load_partial_compatible(plugin_config, datablock_df) -> None:
    await setup_serialization_context(plugin_config)

    datablock: MyDataBlock = await DataBlocks.save(
        MyDataBlock, datablock_df, block_id="b1", block_field=42
    )

    # Simulating a change in the schemas
    datablock_not_compat = MyDataBlockNoCompat(
        block_id=datablock.block_id,
        block_field=datablock.block_field,
        part1=Dataset(
            protocol=datablock.part1.protocol,
            partition_key=datablock.part1.partition_key,
            collection=datablock.part2.collection,
            key=datablock.part1.key,
            datatype="conftest.Part1NoCompat",  # This is just to emulate Part1 has a new schema
            schema=datablock.part1.schema,  # It was saved using the old schema
        ),
        part2=cast(Dataset[Part2Compat], datablock.part2),
    )

    loaded_df = await DataBlocks.load(
        datablock_not_compat, select=["part2"]
    )  # part2 is still compatible

    print(loaded_df.columns)

    assert_frame_equal(
        datablock_df[
            [
                "field0",
                "field3",
                "field4",
                "field5_opt",
                "field6_opt",
                "field7_opt",
                "block_id",
                "block_field",
            ]
        ],
        loaded_df,
    )
