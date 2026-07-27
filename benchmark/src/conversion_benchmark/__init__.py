from __future__ import annotations

import argparse
import gc
import json
import os
import statistics
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass


def _isolate_from_inherited_pythonpath() -> None:
    """Prevent a foreign Python environment from shadowing venv dependencies."""
    inherited_paths = {
        os.path.realpath(path)
        for path in os.environ.pop("PYTHONPATH", "").split(os.pathsep)
        if path
    }
    if inherited_paths:
        sys.path[:] = [
            path
            for path in sys.path
            if os.path.realpath(path or os.curdir) not in inherited_paths
        ]


_isolate_from_inherited_pythonpath()

import numpy as np
import pandas as pd
import polars as pl


@dataclass(frozen=True)
class BenchmarkResult:
    key: str
    label: str
    durations: tuple[float, ...]

    @property
    def median_ms(self) -> float:
        return statistics.median(self.durations) * 1_000

    @property
    def minimum_ms(self) -> float:
        return min(self.durations) * 1_000

    @property
    def maximum_ms(self) -> float:
        return max(self.durations) * 1_000

    def as_dict(self) -> dict[str, str | float]:
        return {
            "key": self.key,
            "label": self.label,
            "median_ms": self.median_ms,
            "minimum_ms": self.minimum_ms,
            "maximum_ms": self.maximum_ms,
        }


def generate_pandas_dataframe(rows: int, seed: int) -> pd.DataFrame:
    """Create reproducible mixed data using explicit, realistic pandas dtypes."""
    if rows < 1:
        raise ValueError("rows must be at least 1")

    rng = np.random.default_rng(seed)
    start = np.datetime64("2020-01-01T00:00:00", "ns")
    timestamps = start + rng.integers(0, 5 * 365 * 24 * 60 * 60, rows).astype(
        "timedelta64[s]"
    )
    labels = np.array(["alpha", "beta", "gamma", "delta"], dtype=object)

    return pd.DataFrame(
        {
            "id": pd.Series(np.arange(rows), dtype="int64"),
            "nullable_count": pd.Series(
                pd.array(rng.integers(0, 10_000, rows), dtype="Int64")
            ).mask(rng.random(rows) < 0.05),
            "value": pd.Series(rng.normal(100.0, 15.0, rows), dtype="float64"),
            "active": pd.Series(rng.random(rows) < 0.5, dtype="bool"),
            "nullable_flag": pd.Series(
                pd.array(rng.random(rows) < 0.5, dtype="boolean")
            ).mask(rng.random(rows) < 0.05),
            "name": pd.Series(
                [f"item-{value:08x}" for value in rng.integers(0, 2**32, rows)],
                dtype="string",
            ),
            "category": pd.Series(
                pd.Categorical(rng.choice(labels, rows), categories=labels)
            ),
            "timestamp": pd.Series(timestamps, dtype="datetime64[ns]"),
            "duration": pd.Series(
                rng.integers(0, 86_400, rows).astype("timedelta64[s]")
            ),
        }
    )


def _measure(
    key: str,
    label: str,
    operation: Callable[[], pd.DataFrame | pl.DataFrame | pl.LazyFrame],
    repeats: int,
    warmups: int,
) -> BenchmarkResult:
    for _ in range(warmups):
        operation()

    durations: list[float] = []
    for _ in range(repeats):
        gc.collect()
        started = time.perf_counter()
        result = operation()
        durations.append(time.perf_counter() - started)
        if isinstance(result, pl.LazyFrame):
            result.collect_schema()

    return BenchmarkResult(key, label, tuple(durations))


def _measure_pandas_to_polars(
    scenario_key: str,
    scenario_label: str,
    dataframe: pd.DataFrame,
    repeats: int,
    warmups: int,
    *,
    nan_to_null: bool,
) -> tuple[BenchmarkResult, BenchmarkResult]:
    convert = lambda: pl.from_pandas(
        dataframe,
        include_index=False,
        nan_to_null=nan_to_null,
    )
    return (
        _measure(
            f"{scenario_key}.pandas_to_polars_df",
            f"{scenario_label}: pandas -> Polars DF",
            convert,
            repeats,
            warmups,
        ),
        _measure(
            f"{scenario_key}.pandas_to_polars_lf",
            f"{scenario_label}: pandas -> Polars LF",
            lambda: convert().lazy(),
            repeats,
            warmups,
        ),
    )


def run_benchmark(
    dataframe: pd.DataFrame, repeats: int, warmups: int
) -> tuple[BenchmarkResult, ...]:
    if repeats < 1:
        raise ValueError("repeats must be at least 1")
    if warmups < 0:
        raise ValueError("warmups cannot be negative")

    polars_dataframe = pl.from_pandas(dataframe, include_index=False)
    polars_lazyframe = polars_dataframe.lazy()

    without_category = dataframe.drop(columns=["category"])
    fixed_width = dataframe[["id", "value", "active"]]

    results = (
        *_measure_pandas_to_polars(
            "full",
            "Full",
            dataframe,
            repeats,
            warmups,
            nan_to_null=True,
        ),
        *_measure_pandas_to_polars(
            "no_category_no_nan_scan",
            "No category/no NaN scan",
            without_category,
            repeats,
            warmups,
            nan_to_null=False,
        ),
        *_measure_pandas_to_polars(
            "fixed_width_no_nan_scan",
            "id/value/active/no scan",
            fixed_width,
            repeats,
            warmups,
            nan_to_null=False,
        ),
        _measure(
            "full.polars_df_to_pandas",
            "Full: Polars DF -> pandas",
            lambda: polars_dataframe.to_pandas(use_pyarrow_extension_array=True),
            repeats,
            warmups,
        ),
        _measure(
            "full.polars_lf_to_pandas",
            "Full: Polars LF -> pandas",
            lambda: polars_lazyframe.collect().to_pandas(
                use_pyarrow_extension_array=True
            ),
            repeats,
            warmups,
        ),
    )
    _validate_conversions(dataframe, polars_dataframe)
    _validate_pandas_to_polars(without_category, nan_to_null=False)
    _validate_pandas_to_polars(fixed_width, nan_to_null=False)
    return results


def _validate_pandas_to_polars(
    pandas_dataframe: pd.DataFrame, *, nan_to_null: bool
) -> None:
    polars_dataframe = pl.from_pandas(
        pandas_dataframe,
        include_index=False,
        nan_to_null=nan_to_null,
    )
    if polars_dataframe.shape != pandas_dataframe.shape:
        raise RuntimeError(
            "shape changed during pandas -> Polars conversion: "
            f"{pandas_dataframe.shape} -> {polars_dataframe.shape}"
        )
    pandas_nulls = int(pandas_dataframe.isna().sum().sum())
    polars_nulls = int(polars_dataframe.null_count().sum_horizontal().item())
    if polars_nulls != pandas_nulls:
        raise RuntimeError("null count changed during pandas -> Polars conversion")


def _validate_conversions(
    pandas_dataframe: pd.DataFrame, polars_dataframe: pl.DataFrame
) -> None:
    _validate_pandas_to_polars(pandas_dataframe, nan_to_null=True)
    pandas_nulls = int(pandas_dataframe.isna().sum().sum())
    polars_nulls = int(polars_dataframe.null_count().sum_horizontal().item())

    roundtrip = polars_dataframe.to_pandas(use_pyarrow_extension_array=True)
    if roundtrip.shape != pandas_dataframe.shape:
        raise RuntimeError(
            "shape changed during Polars -> pandas conversion: "
            f"{polars_dataframe.shape} -> {roundtrip.shape}"
        )
    if int(roundtrip.isna().sum().sum()) != polars_nulls:
        raise RuntimeError("null count changed during Polars -> pandas conversion")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Benchmark pandas/Polars conversion in both directions."
    )
    parser.add_argument("--rows", type=int, default=10_000_000)
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable results without the human report.",
    )
    return parser


def _print_report(
    dataframe: pd.DataFrame, results: Sequence[BenchmarkResult]
) -> None:
    memory_mib = dataframe.memory_usage(index=True, deep=True).sum() / 1024**2
    print(f"Python: {sys.version.split()[0]}")
    print(f"pandas: {pd.__version__}")
    print(f"Polars: {pl.__version__}")
    print(f"Rows: {len(dataframe):,}")
    print(f"Columns: {len(dataframe.columns)}")
    print(f"Pandas memory: {memory_mib:,.1f} MiB")
    print("\nPandas dtypes:")
    print(dataframe.dtypes.to_string())
    label_width = max(len(result.label) for result in results)
    print("\nConversion timings (random-data generation excluded):")
    print(f"{'Conversion':<{label_width}} {'median':>12} {'min':>12} {'max':>12}")
    for result in results:
        print(
            f"{result.label:<{label_width}} {result.median_ms:>9.2f} ms"
            f" {result.minimum_ms:>9.2f} ms {result.maximum_ms:>9.2f} ms"
        )
    print(
        "\nNotes: pandas input is converted eagerly before .lazy(); "
        "LazyFrame -> pandas includes .collect()."
    )


def main(argv: Sequence[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)
    dataframe = generate_pandas_dataframe(args.rows, args.seed)
    results = run_benchmark(dataframe, args.repeats, args.warmups)
    if args.json:
        print(
            json.dumps(
                {
                    "python_version": sys.version.split()[0],
                    "pandas_version": pd.__version__,
                    "polars_version": pl.__version__,
                    "rows": len(dataframe),
                    "results": [result.as_dict() for result in results],
                }
            )
        )
    else:
        _print_report(dataframe, results)
