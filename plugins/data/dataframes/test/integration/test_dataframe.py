from datetime import UTC, datetime, timezone, date

import polars as pl
from polars.testing import assert_series_equal
import pytest

from conftest import DEFAULT_DATE, DEFAULT_DATETIME, MyTestAllTypesData, MyTestAllTypesDefaultValues


def test_coerce_types_happy():
    test_date = datetime.now().date()
    test_datetime = datetime.now(tz=timezone.utc)

    data = MyTestAllTypesData(
        int_value=[0, 1, 2],
        float_value=[1.1, 2.2, 3],
        str_value=["a", "B", "test"],
        date_value=[test_date, test_date, date.fromisoformat("2024-01-01")],
        datetime_value=[
            test_datetime,
            test_datetime,
            datetime.fromisoformat("2024-01-01T00:00:00Z"),
        ],
        bool_value=[True, False, True],
        int_value_optional=[0, 1, None],
        float_value_optional=[1.1, 2.2, None],
        str_value_optional=["a", "B", None],
        date_value_optional=[test_date, None, None],
        datetime_value_optional=[test_datetime, test_datetime, None],
        bool_value_optional=[True, False, None],
    )

    assert_series_equal(
        data.int_value, pl.Series(name="int_value", values=[0, 1, 2], dtype=pl.Int64)
    )
    assert_series_equal(data.float_value, pl.Series(name="float_value", values=[1.1, 2.2, 3.0]))
    assert_series_equal(data.str_value, pl.Series(name="str_value", values=["a", "B", "test"]))
    assert_series_equal(
        data.date_value,
        pl.Series(
            name="date_value",
            values=[
                test_date,
                test_date,
                date.fromisoformat("2024-01-01"),
            ],
            dtype=pl.Date,
        ),
    )
    assert_series_equal(
        data.datetime_value,
        pl.Series(
            name="datetime_value",
            values=[
                test_datetime,
                test_datetime,
                datetime.fromisoformat("2024-01-01T00:00:00Z"),
            ],
            dtype=pl.Datetime,
        ),
    )
    assert_series_equal(data.bool_value, pl.Series(name="bool_value", values=[True, False, True]))
    assert_series_equal(
        data.int_value_optional,
        pl.Series(name="int_value_optional", values=[0, 1, None], dtype=pl.Int64),
    )
    assert_series_equal(
        data.float_value_optional, pl.Series(name="float_value_optional", values=[1.1, 2.2, None])
    )
    assert_series_equal(
        data.str_value_optional, pl.Series(name="str_value_optional", values=["a", "B", None])
    )
    assert_series_equal(
        data.date_value_optional,
        pl.Series(
            name="date_value_optional",
            values=[
                test_date,
                None,
                None,
            ],
        ),
    )
    assert_series_equal(
        data.datetime_value_optional,
        pl.Series(
            name="datetime_value_optional",
            values=[
                test_datetime,
                test_datetime,
                None,
            ],
        ),
    )
    assert_series_equal(
        data.bool_value_optional, pl.Series(name="bool_value_optional", values=[True, False, None])
    )


def test_coerce_types_defaults():
    data = MyTestAllTypesDefaultValues(id=["1", "2", "3"])
    assert_series_equal(
        data.int_value,
        pl.Series(name="int_value", values=[1, 1, 1], dtype=pl.Int64),
    )
    assert_series_equal(
        data.float_value,
        pl.Series(
            name="float_value",
            values=[1.0, 1.0, 1.0],
        ),
    )
    assert_series_equal(
        data.str_value,
        pl.Series(name="str_value", values=["(default)", "(default)", "(default)"]),
    )
    assert_series_equal(
        data.date_value,
        pl.Series(name="date_value", values=[DEFAULT_DATE, DEFAULT_DATE, DEFAULT_DATE]),
    )
    assert_series_equal(
        data.datetime_value,
        pl.Series(
            name="datetime_value",
            values=[DEFAULT_DATETIME, DEFAULT_DATETIME, DEFAULT_DATETIME],
        ),
    )
    assert_series_equal(data.bool_value, pl.Series(name="bool_value", values=[False, False, False]))
    assert_series_equal(
        data.float_value_optional,
        pl.Series(name="float_value_optional", values=[None, None, None], dtype=pl.Float64),
    )
    assert_series_equal(
        data.str_value_optional,
        pl.Series(name="str_value_optional", values=[None, None, None], dtype=pl.String),
    )
    assert_series_equal(
        data.date_value_optional,
        pl.Series(name="date_value_optional", values=[None, None, None], dtype=pl.Date()),
    )
    assert_series_equal(
        data.datetime_value_optional,
        pl.Series(
            name="datetime_value_optional",
            values=[None, None, None],
            dtype=pl.Datetime(time_zone=UTC),
        ),
    )
    assert_series_equal(
        data.bool_value_optional,
        pl.Series(name="bool_value_optional", values=[None, None, None], dtype=pl.Boolean),
    )


def test_coerce_types_none_to_defaults():
    data = MyTestAllTypesDefaultValues(
        id=["1", "2", "3"],
        int_value_optional=None,
        float_value_optional=None,
        str_value_optional=None,
        date_value_optional=None,
        datetime_value_optional=None,
    )
    assert_series_equal(
        data.int_value,
        pl.Series(name="int_value", values=[1, 1, 1], dtype=pl.Int64),
    )
    assert_series_equal(
        data.float_value,
        pl.Series(
            name="float_value",
            values=[1.0, 1.0, 1.0],
        ),
    )
    assert_series_equal(
        data.str_value,
        pl.Series(name="str_value", values=["(default)", "(default)", "(default)"]),
    )
    assert_series_equal(
        data.date_value,
        pl.Series(name="date_value", values=[DEFAULT_DATE, DEFAULT_DATE, DEFAULT_DATE]),
    )
    assert_series_equal(
        data.datetime_value,
        pl.Series(
            name="datetime_value",
            values=[DEFAULT_DATETIME, DEFAULT_DATETIME, DEFAULT_DATETIME],
        ),
    )
    assert_series_equal(
        data.float_value_optional,
        pl.Series(name="float_value_optional", values=[None, None, None], dtype=pl.Float64),
    )
    assert_series_equal(
        data.str_value_optional,
        pl.Series(name="str_value_optional", values=[None, None, None], dtype=pl.String),
    )
    assert_series_equal(
        data.date_value_optional,
        pl.Series(name="date_value_optional", values=[None, None, None], dtype=pl.Date),
    )
    assert_series_equal(
        data.datetime_value_optional,
        pl.Series(
            name="datetime_value_optional",
            values=[None, None, None],
            dtype=pl.Datetime(time_zone=UTC),
        ),
    )


def test_coerce_types_unhappy_bad_types():
    test_date = datetime.now().date()
    test_datetime = datetime.now(tz=timezone.utc)

    with pytest.raises(TypeError):
        MyTestAllTypesDefaultValues(
            id=["1", "2", "3"],
            int_value=[0, 1, "a"],
        )

    with pytest.raises(TypeError):
        MyTestAllTypesDefaultValues(
            id=["1", "2", "3"],
            float_value=[1.1, 2.2, "a"],
        )

    with pytest.raises(TypeError):
        MyTestAllTypesDefaultValues(
            id=["1", "2", "3"],
            date_value=[test_date, test_date, "invalid-date"],
        )

    with pytest.raises(TypeError):
        MyTestAllTypesDefaultValues(
            id=["1", "2", "3"],
            datetime_value=[test_datetime, test_datetime, "invalid-date"],
        )

    with pytest.raises(TypeError):
        MyTestAllTypesDefaultValues(
            id=["1", "2", "3"],
            int_value_optional=[None, None, "a"],
        )

    with pytest.raises(TypeError):
        MyTestAllTypesDefaultValues(
            id=["1", "2", "3"],
            float_value_optional=[None, None, "a"],
        )

    with pytest.raises(TypeError):
        MyTestAllTypesDefaultValues(
            id=["1", "2", "3"],
            str_value_optional=[None, None, 123],
        )


def test_coerce_types_unhappy_none_fields():
    test_date = datetime.now().date()
    test_datetime = datetime.now(tz=timezone.utc)

    with pytest.raises(TypeError):
        MyTestAllTypesData(
            int_value=None,
            bool_value=[True, True, False],
            float_value=[1.1, 2.2, 3],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(TypeError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            bool_value=None,
            float_value=[1.1, 2.2, 3],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(TypeError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            bool_value=[True, True, False],
            float_value=None,
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(TypeError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            bool_value=[True, True, False],
            float_value=[1.1, 2.2, 3],
            str_value=None,
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(TypeError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            bool_value=[True, True, False],
            float_value=[1.1, 2.2, 3],
            str_value=["a", "B", 42],
            date_value=None,
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(TypeError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            bool_value=[True, True, False],
            float_value=[1.1, 2.2, 3],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=None,
        )


def test_coerce_types_unhappy_none_values():
    test_date = datetime.now().date()
    test_datetime = datetime.now(tz=timezone.utc)

    with pytest.raises(TypeError):
        MyTestAllTypesData(
            int_value=[1, 2, None],
            float_value=[1.1, 2.2, 3],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(TypeError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            float_value=[1.1, 2.2, None],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(TypeError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            float_value=[1.1, 2.2, 3],
            str_value=["a", "b", None],
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(TypeError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            float_value=[1.1, 2.2, 3],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, None],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(TypeError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            float_value=[1.1, 2.2, 3],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=[test_datetime, None, None],
        )


def test_coerce_types_unhappy_missing_fields():
    test_date = datetime.now().date()
    test_datetime = datetime.now(tz=timezone.utc)

    with pytest.raises(TypeError):
        MyTestAllTypesData(
            float_value=[1.1, 2.2, 3],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(TypeError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(TypeError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            float_value=[1.1, 2.2, 3],
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(TypeError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            float_value=[1.1, 2.2, 3],
            str_value=["a", "B", 42],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(TypeError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            float_value=[1.1, 2.2, 3],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, "2024-01-01"],
        )
