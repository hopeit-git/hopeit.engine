from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from conftest import MyTestAllTypesData


def test_coerce_types_happy():
    test_date = datetime.now().date()
    test_datetime = datetime.now(tz=timezone.utc)

    data = MyTestAllTypesData(
        int_value=[0, 1, 2.5],
        float_value=[1.1, 2.2, 3],
        str_value=["a", "B", 42],
        date_value=[test_date, test_date, "2024-01-01"],
        datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        float_value_opt=[1.1, 2.2, None],
        date_value_opt=[test_date, None, None],
        datetime_value_opt=[test_datetime, test_datetime, None],
    )

    pd.testing.assert_series_equal(
        data.int_value, pd.Series([0, 1, 2], name="int_value")
    )
    pd.testing.assert_series_equal(
        data.float_value, pd.Series([1.1, 2.2, 3.0], name="float_value")
    )
    pd.testing.assert_series_equal(
        data.str_value, pd.Series(["a", "B", "42"], name="str_value")
    )
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


def test_coerce_types_none_values():
    test_date = datetime.now().date()
    test_datetime = datetime.now(tz=timezone.utc)

    data = MyTestAllTypesData(
        int_value=[0, 1, 2.5],
        str_value=["a", "B", None],
        float_value=[1.1, 2.2, None],
        date_value=[test_date, None, None],
        datetime_value=[test_datetime, test_datetime, None],
    )
    pd.testing.assert_series_equal(
        data.float_value, pd.Series([1.1, 2.2, np.nan], name="float_value")
    )
    pd.testing.assert_series_equal(
        data.str_value, pd.Series(["a", "B", "None"], name="str_value")
    )
    pd.testing.assert_series_equal(
        data.date_value,
        pd.Series([pd.Timestamp(test_date), pd.NaT, pd.NaT], name="date_value"),
    )
    pd.testing.assert_series_equal(
        data.datetime_value,
        pd.Series(
            [pd.Timestamp(test_datetime), pd.Timestamp(test_datetime), pd.NaT],
            name="datetime_value",
        ),
    )


def test_coerce_types_defaults():
    data = MyTestAllTypesData(
        int_value=[0, 1, 2.5],
        float_value=None,
        str_value=None,
        date_value=None,
        datetime_value=None,
    )

    pd.testing.assert_series_equal(
        data.float_value,
        pd.Series([np.nan, np.nan, np.nan], name="float_value"),
    )
    pd.testing.assert_series_equal(
        data.str_value, pd.Series(["None", "None", "None"], name="str_value")
    )
    pd.testing.assert_series_equal(
        data.date_value,
        pd.Series([pd.NaT, pd.NaT, pd.NaT], name="date_value"),
    )
    pd.testing.assert_series_equal(
        data.datetime_value,
        pd.Series(
            [pd.NaT, pd.NaT, pd.NaT],
            name="datetime_value",
            dtype="datetime64[ns, UTC]"
        ),
    )


def test_coerce_types_unhappy():
    test_date = datetime.now().date()
    test_datetime = datetime.now(tz=timezone.utc)

    with pytest.raises(ValueError):
        MyTestAllTypesData(
            int_value=[0, 1, "a"],
            float_value=[1.1, 2.2, 3],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(ValueError):
        MyTestAllTypesData(
            int_value=[0, 1, 2.5],
            float_value=[1.1, 2.2, "a"],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, "2024-01-01"],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(ValueError):
        MyTestAllTypesData(
            int_value=[0, 1, 2.5],
            float_value=[1.1, 2.2, 3.3],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, "invalid-date"],
            datetime_value=[test_datetime, test_datetime, "2024-01-01T00:00:00Z"],
        )

    with pytest.raises(ValueError):
        MyTestAllTypesData(
            int_value=[0, 1, 2.5],
            float_value=[1.1, 2.2, 3.3],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, test_date],
            datetime_value=[test_datetime, test_datetime, "invalid-date"],
        )

    with pytest.raises(TypeError):
        MyTestAllTypesData(
            int_value=None,
            float_value=[1.1, 2.2, 3.3],
            str_value=["a", "B", 42],
            date_value=[test_date, test_date, test_date],
            datetime_value=[test_datetime, test_datetime, test_datetime],
        )
