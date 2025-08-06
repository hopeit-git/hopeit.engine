from typing import TYPE_CHECKING, Any


try:
    import polars

    DataFrame = polars.DataFrame
    LazyFrame = polars.LazyFrame
    Schema = polars.Schema
    Series = polars.Series

    read_parquet = polars.read_parquet
    scan_parquet = polars.scan_parquet
    concat = polars.concat
    lit = polars.lit
    col = polars.col

except ImportError:
    HOPEIT_DATAFRAMES_POLARS_IS_MOCK = True

    if TYPE_CHECKING:
        # Mock of polars to handle `@dataframe` annotation without `polars` installed during type checking
        class DataFrame:  # type: ignore
            def __init__(self, *args, **kwargs) -> None:
                pass

            def __getattribute__(self, name) -> Any:
                pass

            def __getitem__(*args, **kwargs) -> Any:
                pass

        class LazyFrame:  # type: ignore
            def __getattribute__(self, name) -> Any:
                pass

        class Schema:  # type: ignore
            def __getattribute__(self, name) -> Any:
                pass

        class Series:  # type: ignore
            def __init__(self, *args, **kwargs) -> None:
                pass

            def __getattribute__(self, name) -> Any:
                pass
