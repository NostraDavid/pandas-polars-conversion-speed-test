from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare the shared benchmark under pandas 2 and pandas 3."
    )
    parser.add_argument("--rows", type=int, default=10_000_000)
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def _run_environment(
    root: Path,
    project: str,
    executable: str,
    *,
    rows: int,
    repeats: int,
    warmups: int,
    seed: int,
) -> dict[str, Any]:
    environment = os.environ.copy()
    for name in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"):
        environment.pop(name, None)

    completed = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            str(root / project),
            executable,
            "--rows",
            str(rows),
            "--repeats",
            str(repeats),
            "--warmups",
            str(warmups),
            "--seed",
            str(seed),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    return json.loads(completed.stdout)


def _print_comparison(pandas2: dict[str, Any], pandas3: dict[str, Any]) -> None:
    p2_results = {result["key"]: result for result in pandas2["results"]}
    p3_results = {result["key"]: result for result in pandas3["results"]}
    if p2_results.keys() != p3_results.keys():
        raise RuntimeError("pandas 2 and pandas 3 returned different benchmark sets")

    print(
        f"pandas {pandas2['pandas_version']} vs pandas {pandas3['pandas_version']} "
        f"({pandas2['rows']:,} rows, Polars {pandas2['polars_version']})"
    )
    print(
        "\nSpeedup = pandas 2 time / pandas 3 time; "
        "positive percentages favor pandas 3.\n"
    )
    label_width = max(len(result["label"]) for result in p2_results.values())
    print(
        f"{'Conversion':<{label_width}} {'pandas 2':>11} {'pandas 3':>11} "
        f"{'delta':>10} {'speedup':>9} {'time reduction':>15} {'throughput':>12}"
    )
    for key, p2_result in p2_results.items():
        p2_ms = float(p2_result["median_ms"])
        p3_ms = float(p3_results[key]["median_ms"])
        speedup = p2_ms / p3_ms
        time_reduction = (1 - p3_ms / p2_ms) * 100
        throughput_gain = (speedup - 1) * 100
        print(
            f"{p2_result['label']:<{label_width}} "
            f"{p2_ms:>8.2f} ms {p3_ms:>8.2f} ms "
            f"{p2_ms - p3_ms:>7.2f} ms {speedup:>8.2f}x "
            f"{time_reduction:>13.1f}% {throughput_gain:>10.1f}%"
        )


def main() -> None:
    args = _build_parser().parse_args()
    root = Path(__file__).resolve().parents[3]
    pandas2 = _run_environment(
        root,
        "p2p",
        "p2p",
        rows=args.rows,
        repeats=args.repeats,
        warmups=args.warmups,
        seed=args.seed,
    )
    pandas3 = _run_environment(
        root,
        "p3p",
        "p3p",
        rows=args.rows,
        repeats=args.repeats,
        warmups=args.warmups,
        seed=args.seed,
    )
    _print_comparison(pandas2, pandas3)


if __name__ == "__main__":
    main()
