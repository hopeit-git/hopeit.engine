from dataclasses import dataclass
from datetime import datetime, timezone
from hopeit.dataobjects import dataobject
import numpy as np

import pandas as pd

from hopeit.dataobjects.payload import Payload
from hopeit.dataframes import dataframe, DataFrame


@dataframe
@dataclass
class SomeData:
    id: int
    name: str
    value: float


@dataframe
@dataclass
class SmallData:
    name: str
    value: float


@dataframe(schema=False)
@dataclass
class FreeData:
    name: str
    value: float


@dataframe
@dataclass
class OtherData:
    id: int
    score: float


@dataframe
@dataclass
class MergedData:
    id: int
    name: str
    value: float
    score: float
    ratio: float
    ts: datetime


__steps__ = [
    "filter",
    "transform",
]


def filter(data_: DataFrame[SomeData]) -> SomeData:
    return data_[data_.id != 1]


def final(data_: DataFrame[SomeData]) -> SmallData:
    return DataFrame(SmallData).from_df(data_.df.loc[data_.id == 5, ["name", "value"]])


def transform(data: SomeData) -> OtherData:
    return OtherData(id=data.id, score=data.value * 100.0)


def merge(data: DataFrame[SomeData], other_data: DataFrame[OtherData]) -> MergedData:
    merged_df = data.df.merge(other_data.df, on="id")
    return DataFrame(MergedData).from_df(
        merged_df,
        ratio=merged_df.score / merged_df.value,
        ts=datetime.now(tz=timezone.utc),
    )


def adjust(data: DataFrame[MergedData]) -> MergedData:
    new_value = pd.Series(data.value - 10 * data.id)
    new_value[new_value < 0] = 1.0 - new_value
    ratio = data.score / new_value
    ratio[ratio == np.inf] = 0.0
    return DataFrame(MergedData).from_df(
        DataFrame(data).df,
        value=new_value,
        ratio=ratio,
    )


def test() -> None:
    df = pd.DataFrame(
        [
            {"id": 0, "name": "test", "value": 40.5},
            {"id": 1, "name": "test", "value": 41.5},
            {"id": 2, "name": "test", "value": 42.5},
            {"id": 3, "name": "test", "value": 43.5},
            {"id": 4, "name": "test", "value": 40.0},
            {"id": 5, "name": "test", "value": 45.5},
        ]
    )
    data = DataFrame(SomeData).from_df(df)
    print("data\n", data.df, "\n", data.to_json())
    data = filter(data)
    print("filter\n", data.df, "\n", data.to_json())
    small = DataFrame(final(data))
    print("small\n", small.df, "\n", small.to_json())
    free = DataFrame(FreeData).from_df(small.df)
    print("free\n", free.df, "\n", free.to_json())

    other_data = DataFrame(transform(data))
    print("other_data\n", other_data.df, "\n", other_data.to_json())

    merged_data = DataFrame(merge(data, other_data))
    print("merged_data\n", merged_data.df, "\n", merged_data.to_json())

    adjusted_data = DataFrame(adjust(merged_data))
    print("adjusted_data\n", adjusted_data.df, "\n", adjusted_data.to_json())
    print("merged_data\n", merged_data.df, "\n", merged_data.to_json())
    print("other_data\n", other_data.df, "\n", other_data.to_json())
    print("data\n", data.df, "\n", data.to_json())

    print("Payload to_json\n", Payload.to_json(merged_data))
    print("Payload to_dict\n", Payload.to_obj(merged_data))

    json_str = Payload.to_json(merged_data)
    print("Payload from_json\n", Payload.from_json(json_str, datatype=MergedData))

    dict_values = Payload.to_obj(merged_data)
    print("Payload from_dict\n", Payload.from_obj(dict_values, datatype=MergedData))

    assert True


if __name__ == "__main__":
    test()
