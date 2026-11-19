# Dataframes plugin

This plugin supplies typed Polars containers and persisted dataset/datablock
references. Its Hopeit app initializes serialization and the storage registry.
Use the root guide for general dataobject and event conventions.

## Usage

Install `hopeit.dataframes[polars]` when performing dataframe calculations. Load
[config/plugin-config.json](config/plugin-config.json) with the server, adapting
its registry and database locations. The `setup.dataframes` SETUP event configures
serialization; `setup.register_database` registers additional databases.

```python
import polars as pl

from hopeit.dataframes import DataFrames, dataframe
from hopeit.dataobjects import dataclass


@dataframe
@dataclass
class FeatureRows:
    item_id: str
    score: float | None = None


rows: FeatureRows = DataFrames.from_df(
    FeatureRows, pl.DataFrame({"item_id": ["a", "b"]})
)
frame: pl.DataFrame = DataFrames.df(rows)
```

- `DataFrames.schema(Type)` exposes the schema; `DataFrames.to_dataobjects(value)`
  supplies typed row objects for JSON responses.
- Normal construction selects declared columns, applies the schema, supplies
  declared defaults, and checks non-nullable fields. The example's missing score
  column becomes typed nulls. Nullable typing alone does not supply a default;
  column presence does not prove that a feature is enabled or populated.
- Use `Dataset.save` / `Dataset.load` for persisted `Dataset[T]` references.
  Consumers need compatible type registration and access to the configured
  storage. Send references instead of large matrices in dataset-based pipelines.
- Use `DataBlocks` for dataobjects containing multiple related dataset fields.
  Follow the [dataframes example](../../../apps/examples/dataframes-example/src/dataframes_example/),
  particularly `iris.py`, `prepare_data.py`, and `predict_offline.py`.
- Keep storage partition timestamps distinct from local business dates; preserve
  aware UTC instants. Give separate output blocks unique storage keys.

## Development

Check [dataframe construction](src/hopeit/dataframes/dataframe.py),
[dataset serialization](src/hopeit/dataframes/serialization/), and
[integration tests](test/integration/) when changing schemas or persistence.
Exercise missing/defaulted columns and real save/load conversion where affected.

Run from the repository root:

```sh
make PLUGINFOLDER=plugins/data/dataframes lint-plugin
make PLUGINFOLDER=plugins/data/dataframes test-plugin
```
