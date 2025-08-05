from typing import TYPE_CHECKING


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
        # Mock of polars to handle `@dataframe` annotation without `polars` installed
        class DataFrame:  # type: ignore
            pass

        class LazyFrame:  # type: ignore
            pass

        class Schema:  # type: ignore
            pass

        class Series:  # type: ignore
            pass
