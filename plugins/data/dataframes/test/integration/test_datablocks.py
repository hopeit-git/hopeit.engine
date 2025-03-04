import os
from typing import cast
from hopeit.dataframes.datablocks import TempDataBlock
import numpy as np
import pandas as pd

from hopeit.dataframes import DataBlocks, Dataset
import pytest

from conftest import (
    MyDataBlock,
    MyDataBlockCompat,
    MyDataBlockItem,
    Part1,
    Part2,
    Part2Compat,
    get_saved_file_path,
    setup_serialization_context,
)


async def test_datablock_creation_and_load(plugin_config, datablock_df) -> None:
    await setup_serialization_context(plugin_config)

    datablock = await DataBlocks.from_df(MyDataBlock, datablock_df, block_id="b1", block_field=42)

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
    loaded_df = await DataBlocks.df(datablock)

    pd.testing.assert_frame_equal(
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

    # test get dataframe
    loaded_df = await DataBlocks.df(datablock, select=["part1"])

    pd.testing.assert_frame_equal(
        datablock_df[["field0", "field1", "field2", "block_id", "block_field"]],
        loaded_df,
    )

    # test get dataframe
    loaded_df = await DataBlocks.df(datablock, select=["part2"])

    pd.testing.assert_frame_equal(
        datablock_df[["field0", "field3", "field4", "field5_opt", "block_id", "block_field"]],
        loaded_df,
    )


async def test_datablock_custom_database(plugin_config, datablock_df) -> None:
    await setup_serialization_context(plugin_config)

    datablock = await DataBlocks.from_df(
        MyDataBlock, datablock_df, datablock_database_key="test_db", block_id="b1", block_field=42
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
    loaded_df = await DataBlocks.df(datablock)

    pd.testing.assert_frame_equal(
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

    datablock = await DataBlocks.from_df(
        MyDataBlock,
        datablock_df,
        datablock_database_key="test_db",
        datablock_group_key="datablock/test_group",
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
    loaded_df = await DataBlocks.df(datablock)

    pd.testing.assert_frame_equal(
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

    datablock = await DataBlocks.from_df(
        MyDataBlock,
        datablock_df,
        datablock_database_key="test_db",
        datablock_group_key="datablock/test_group",
        datablock_collection="mycollection",
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
    loaded_df = await DataBlocks.df(datablock)

    pd.testing.assert_frame_equal(
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

    pd.testing.assert_frame_equal(datablock_df, new_datablock.df)


async def test_schema_evolution_compatible(plugin_config, datablock_df) -> None:
    await setup_serialization_context(plugin_config)

    datablock: MyDataBlock = await DataBlocks.from_df(
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
    loaded_df = await DataBlocks.df(datablock_compat)

    datablock_df["field6_opt"] = np.nan
    datablock_df["field7_opt"] = pd.Series(np.nan, dtype=object)

    pd.testing.assert_frame_equal(
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

    datablock: MyDataBlock = await DataBlocks.from_df(
        MyDataBlock, datablock_df, block_id="b1", block_field=42
    )

    # Simulating a change in the schemas
    datablock_not_compat = MyDataBlockCompat(
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
        await DataBlocks.df(datablock_not_compat)


async def test_schema_evolution_load_partial_compatible(plugin_config, datablock_df) -> None:
    await setup_serialization_context(plugin_config)

    datablock: MyDataBlock = await DataBlocks.from_df(
        MyDataBlock, datablock_df, block_id="b1", block_field=42
    )

    # Simulating a change in the schemas
    datablock_not_compat = MyDataBlockCompat(
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

    loaded_df = await DataBlocks.df(
        datablock_not_compat, select=["part2"]
    )  # part2 is still compatible

    pd.testing.assert_frame_equal(
        datablock_df[
            [
                "field0",
                "field3",
                "field4",
                "field5_opt",
                "block_id",
                "block_field",
            ]
        ],
        loaded_df,
    )
