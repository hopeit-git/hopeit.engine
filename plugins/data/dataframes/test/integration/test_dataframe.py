from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from conftest import DEFAULT_DATE, DEFAULT_DATETIME, MyTestAllTypesData, MyTestAllTypesDefaultValues


def test_coerce_types_happy():
    test_date = datetime.now().date()
    test_datetime = datetime.now(tz=timezone.utc)

    data = MyTestAllTypesData(
        int_value=[0, 1, 2],
        float_value=[1.1, 2.2, 3],
        str_value=["a", "B", 42],
        date_value=[test_date, test_date, "2024-01-01"],
        datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        bool_value=[True, False, True],
        int_value_optional=[0, 1, None],
        float_value_optional=[1.1, 2.2, None],
        str_value_optional=["a", "B", None],
        date_value_optional=[test_date, None, None],
        datetime_value_optional=[test_datetime, test_datetime, None],
        bool_value_optional=[True, False, None],
    )

    pd.testing.assert_series_equal(data.int_value, pd.Series([0, 1, 2], name="int_value"))
    pd.testing.assert_series_equal(data.float_value, pd.Series([1.1, 2.2, 3.0], name="float_value"))
    pd.testing.assert_series_equal(data.str_value, pd.Series(["a", "B", "42"], name="str_value"))
    pd.testing.assert_series_equal(
        data.date_value,
        pd.Series(
            [
                pd.Timestamp(test_date),
                pd.Timestamp(test_date),
                pd.Timestamp("2024-01-01"),
            ],
            name="date_value",
        ),
    )
    pd.testing.assert_series_equal(
        data.datetime_value,
        pd.Series(
            [
                pd.Timestamp(test_datetime),
                pd.Timestamp(test_datetime),
                pd.Timestamp("2024-01-01T00:00:00Z"),
            ],
            name="datetime_value",
        ),
    )
    pd.testing.assert_series_equal(
        data.bool_value, pd.Series([True, False, True], name="bool_value")
    )
    pd.testing.assert_series_equal(
        data.int_value_optional, pd.Series([0, 1, np.nan], name="int_value_optional")
    )
    pd.testing.assert_series_equal(
        data.float_value_optional, pd.Series([1.1, 2.2, np.nan], name="float_value_optional")
    )
    pd.testing.assert_series_equal(
        data.str_value_optional, pd.Series(["a", "B", np.nan], name="str_value_optional")
    )
    pd.testing.assert_series_equal(
        data.date_value_optional,
        pd.Series(
            [
                pd.Timestamp(test_date),
                pd.NaT,
                pd.NaT,
            ],
            name="date_value_optional",
        ),
    )
    pd.testing.assert_series_equal(
        data.datetime_value_optional,
        pd.Series(
            [
                pd.Timestamp(test_datetime),
                pd.Timestamp(test_datetime),
                pd.NaT,
            ],
            name="datetime_value_optional",
        ),
    )
    pd.testing.assert_series_equal(
        data.bool_value_optional, pd.Series([True, False, np.nan], name="bool_value_optional")
    )


def test_coerce_types_defaults():
    data = MyTestAllTypesDefaultValues(id=["1", "2", "3"])
    pd.testing.assert_series_equal(
        data.int_value,
        pd.Series([1, 1, 1], name="int_value"),
    )
    pd.testing.assert_series_equal(
        data.float_value,
        pd.Series([1.0, 1.0, 1.0], name="float_value"),
    )
    pd.testing.assert_series_equal(
        data.str_value,
        pd.Series(["(default)", "(default)", "(default)"], name="str_value", dtype="object"),
    )
    pd.testing.assert_series_equal(
        data.date_value,
        pd.Series(
            [DEFAULT_DATE, DEFAULT_DATE, DEFAULT_DATE], name="date_value", dtype="datetime64[ns]"
        ),
    )
    pd.testing.assert_series_equal(
        data.datetime_value,
        pd.Series(
            [DEFAULT_DATETIME, DEFAULT_DATETIME, DEFAULT_DATETIME],
            name="datetime_value",
            dtype="datetime64[ns, UTC]",
        ),
    )
    pd.testing.assert_series_equal(
        data.bool_value, pd.Series([False, False, False], name="bool_value")
    )
    pd.testing.assert_series_equal(
        data.float_value_optional,
        pd.Series([np.nan, np.nan, np.nan], name="float_value_optional"),
    )
    pd.testing.assert_series_equal(
        data.str_value_optional,
        pd.Series([np.nan, np.nan, np.nan], name="str_value_optional", dtype="object"),
    )
    pd.testing.assert_series_equal(
        data.date_value_optional,
        pd.Series([pd.NaT, pd.NaT, pd.NaT], name="date_value_optional", dtype="datetime64[ns]"),
    )
    pd.testing.assert_series_equal(
        data.datetime_value_optional,
        pd.Series(
            [pd.NaT, pd.NaT, pd.NaT], name="datetime_value_optional", dtype="datetime64[ns, UTC]"
        ),
    )
    pd.testing.assert_series_equal(
        data.bool_value_optional,
        pd.Series([np.nan, np.nan, np.nan], dtype=object, name="bool_value_optional"),
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
    pd.testing.assert_series_equal(
        data.int_value,
        pd.Series([1, 1, 1], name="int_value"),
    )
    pd.testing.assert_series_equal(
        data.float_value,
        pd.Series([1.0, 1.0, 1.0], name="float_value"),
    )
    pd.testing.assert_series_equal(
        data.str_value,
        pd.Series(["(default)", "(default)", "(default)"], name="str_value", dtype="object"),
    )
    pd.testing.assert_series_equal(
        data.date_value,
        pd.Series(
            [DEFAULT_DATE, DEFAULT_DATE, DEFAULT_DATE], name="date_value", dtype="datetime64[ns]"
        ),
    )
    pd.testing.assert_series_equal(
        data.datetime_value,
        pd.Series(
            [DEFAULT_DATETIME, DEFAULT_DATETIME, DEFAULT_DATETIME],
            name="datetime_value",
            dtype="datetime64[ns, UTC]",
        ),
    )
    pd.testing.assert_series_equal(
        data.float_value_optional,
        pd.Series([np.nan, np.nan, np.nan], name="float_value_optional"),
    )
    pd.testing.assert_series_equal(
        data.str_value_optional,
        pd.Series([np.nan, np.nan, np.nan], name="str_value_optional", dtype="object"),
    )
    pd.testing.assert_series_equal(
        data.date_value_optional,
        pd.Series([pd.NaT, pd.NaT, pd.NaT], name="date_value_optional", dtype="datetime64[ns]"),
    )
    pd.testing.assert_series_equal(
        data.datetime_value_optional,
        pd.Series(
            [pd.NaT, pd.NaT, pd.NaT], name="datetime_value_optional", dtype="datetime64[ns, UTC]"
        ),
    )


def test_coerce_types_unhappy_bad_types():
    test_date = datetime.now().date()
    test_datetime = datetime.now(tz=timezone.utc)

    with pytest.raises(ValueError):
        MyTestAllTypesDefaultValues(
            id=["1", "2", "3"],
            int_value=[0, 1, "a"],
        )

    with pytest.raises(ValueError):
        MyTestAllTypesDefaultValues(
            id=["1", "2", "3"],
            float_value=[1.1, 2.2, "a"],
        )

    with pytest.raises(ValueError):
        MyTestAllTypesDefaultValues(
            id=["1", "2", "3"],
            date_value=[test_date, test_date, "invalid-date"],
        )

    with pytest.raises(ValueError):
        MyTestAllTypesDefaultValues(
            id=["1", "2", "3"],
            datetime_value=[test_datetime, test_datetime, "invalid-date"],
        )

    with pytest.raises(ValueError):
        MyTestAllTypesDefaultValues(
            id=["1", "2", "3"],
            int_value=None,
        )

    with pytest.raises(ValueError):
        MyTestAllTypesDefaultValues(
            id=["1", "2", "3"],
            float_value=None,
        )

    with pytest.raises(ValueError):
        MyTestAllTypesDefaultValues(
            id=["1", "2", "3"],
            str_value=None,
        )


def test_coerce_types_unhappy_none_fields():
    test_date = datetime.now().date()
    test_datetime = datetime.now(tz=timezone.utc)

    with pytest.raises(ValueError):
        MyTestAllTypesData(
            int_value=None,
            float_value=[1.1, 2.2, 3],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(ValueError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            float_value=None,
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(ValueError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            float_value=[1.1, 2.2, 3],
            str_value=None,
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(ValueError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            float_value=[1.1, 2.2, 3],
            str_value=["a", "B", 42],
            date_value=None,
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(ValueError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            float_value=[1.1, 2.2, 3],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=None,
        )


def test_coerce_types_unhappy_none_values():
    test_date = datetime.now().date()
    test_datetime = datetime.now(tz=timezone.utc)

    with pytest.raises(ValueError):
        MyTestAllTypesData(
            int_value=[1, 2, None],
            float_value=[1.1, 2.2, 3],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(ValueError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            float_value=[1.1, 2.2, None],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(ValueError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            float_value=[1.1, 2.2, 3],
            str_value=["a", "b", None],
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(ValueError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            float_value=[1.1, 2.2, 3],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, None],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(ValueError):
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

    with pytest.raises(KeyError):
        MyTestAllTypesData(
            float_value=[1.1, 2.2, 3],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(KeyError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(KeyError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            float_value=[1.1, 2.2, 3],
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(KeyError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            float_value=[1.1, 2.2, 3],
            str_value=["a", "B", 42],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(KeyError):
        MyTestAllTypesData(
            int_value=[1, 2, 3],
            float_value=[1.1, 2.2, 3],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, "2024-01-01"],
        )
