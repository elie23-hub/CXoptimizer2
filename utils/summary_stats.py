"""
Column summary statistics for the upload data preview.
Computed on original data before imputation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

STAT_ROWS: list[tuple[str, str]] = [
    ("mean", "Mean"),
    ("min", "Min"),
    ("max", "Max"),
    ("stdev", "Stdev"),
    ("missing", "Missing"),
    ("frequencies", "Responses"),
]

DASH = "—"


@dataclass(frozen=True)
class SummaryScale:
    lo: int
    hi: int
    cant_say: int


def _is_nan_like(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, float) and np.isnan(val):
        return True
    return bool(pd.isna(val))


def _valid_rating(val: Any, scale: SummaryScale) -> bool:
    if _is_nan_like(val):
        return False
    if isinstance(val, str) and val.strip() == "":
        return False
    try:
        n = int(round(float(val)))
        return scale.lo <= n <= scale.hi
    except (TypeError, ValueError):
        return False


def _cant_say(val: Any, scale: SummaryScale) -> bool:
    if _is_nan_like(val):
        return False
    if isinstance(val, str) and val.strip() == "":
        return False
    try:
        return int(round(float(val))) == scale.cant_say
    except (TypeError, ValueError):
        return False


def _is_missing_cell(val: Any, scale: SummaryScale) -> bool:
    """Can't-say code or empty cell (matches upload missing counts)."""
    return _cant_say(val, scale) or (
        not _valid_rating(val, scale)
        and (isinstance(val, str) and val.strip() == "" or _is_nan_like(val))
    )


def _id_column(col_def: dict[str, str]) -> bool:
    col_type = col_def.get("type", "")
    if col_type == "id":
        return True
    key = col_def.get("key", "").lower()
    label = col_def.get("label", "").lower()
    return "id" in key or key.endswith("id") or "id" in label


def _rating_column(col_def: dict[str, str]) -> bool:
    return col_def.get("type") in ("rating", "osat")


def compute_summary_stats(
    df: pd.DataFrame,
    columns: list[dict[str, str]],
    *,
    scale: SummaryScale | None = None,
) -> dict[str, Any]:
    """Build summary table: rows = stats, columns = attributes (pre-imputation)."""
    if scale is None:
        scale = SummaryScale(lo=1, hi=5, cant_say=6)

    values_by_stat: dict[str, dict[str, str]] = {sid: {} for sid, _ in STAT_ROWS}

    for col_def in columns:
        key = col_def["key"]
        if key not in df.columns or _id_column(col_def):
            for sid, _ in STAT_ROWS:
                values_by_stat[sid][key] = DASH
            continue

        series = df[key]

        if _rating_column(col_def):
            missing = sum(1 for val in series if _is_missing_cell(val, scale))
            responses = sum(1 for val in series if _valid_rating(val, scale))
            values_by_stat["missing"][key] = str(missing)
            values_by_stat["frequencies"][key] = str(responses)

            ratings = [
                float(val)
                for val in series
                if _valid_rating(val, scale)
            ]
            if not ratings:
                for sid in ("mean", "min", "max", "stdev"):
                    values_by_stat[sid][key] = DASH
                continue

            arr = np.array(ratings, dtype=float)
            values_by_stat["mean"][key] = f"{float(arr.mean()):.2f}"
            values_by_stat["min"][key] = f"{float(arr.min()):.2f}"
            values_by_stat["max"][key] = f"{float(arr.max()):.2f}"
            values_by_stat["stdev"][key] = (
                f"{float(arr.std(ddof=0)):.2f}" if len(arr) > 1 else "0.00"
            )
            continue

        # Non-rating, non-id columns: basic numeric stats if possible
        numeric = pd.to_numeric(series, errors="coerce")
        valid = numeric.dropna()
        missing = int(numeric.isna().sum())
        values_by_stat["missing"][key] = str(missing)
        values_by_stat["frequencies"][key] = str(int(valid.count()))

        if valid.empty:
            for sid in ("mean", "min", "max", "stdev"):
                values_by_stat[sid][key] = DASH
            continue

        values_by_stat["mean"][key] = f"{float(valid.mean()):.2f}"
        values_by_stat["min"][key] = f"{float(valid.min()):.2f}"
        values_by_stat["max"][key] = f"{float(valid.max()):.2f}"
        values_by_stat["stdev"][key] = (
            f"{float(valid.std(ddof=0)):.2f}" if len(valid) > 1 else "0.00"
        )

    rows = [
        {"id": sid, "label": label, "values": values_by_stat[sid]}
        for sid, label in STAT_ROWS
    ]
    return {
        "columns": columns,
        "rows": rows,
        "n_rows": len(df),
    }


def _column_ratings_array(series: pd.Series, scale: SummaryScale) -> np.ndarray:
    """In-scale ratings only; can't-say, blank, and out-of-range → NaN."""
    numeric = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
    valid = (numeric >= scale.lo) & (numeric <= scale.hi)
    return np.where(valid, numeric, np.nan)


def compute_respondent_missing_table(
    df: pd.DataFrame,
    statement_cols: list[str],
    *,
    id_column: str | None = None,
    scale: SummaryScale | None = None,
) -> dict[str, Any]:
    """Missing-value count and rate per respondent on pre-imputation statement data."""
    scale = scale or SummaryScale(lo=1, hi=5, cant_say=6)
    cols = [c for c in statement_cols if c in df.columns]
    if df.empty or not cols:
        return {
            "rows": [],
            "n_total": 0,
            "n_statements": len(cols),
            "id_column": id_column or "",
            "stats": {},
        }

    rows: list[dict[str, Any]] = []
    missing_counts: list[int] = []
    missing_rates: list[float] = []
    n_statements = len(cols)

    for i in range(len(df)):
        row = df.iloc[i]
        missing_count = sum(1 for col in cols if _is_missing_cell(row[col], scale))
        missing_rate = (missing_count / n_statements * 100.0) if n_statements else 0.0

        label = str(i + 1)
        if id_column and id_column in df.columns:
            raw_id = row[id_column]
            if not _is_nan_like(raw_id) and str(raw_id).strip() != "":
                label = str(raw_id).strip()

        rows.append(
            {
                "index": i + 1,
                "label": label,
                "missing_count": missing_count,
                "missing_rate": round(float(missing_rate), 1),
            }
        )
        missing_counts.append(missing_count)
        missing_rates.append(missing_rate)

    count_arr = np.array(missing_counts, dtype=float)
    rate_arr = np.array(missing_rates, dtype=float)

    return {
        "rows": rows,
        "n_total": len(df),
        "n_statements": n_statements,
        "id_column": id_column or "",
        "stats": {
            "mean_missing_count": round(float(count_arr.mean()), 2),
            "max_missing_count": int(count_arr.max()) if len(count_arr) else 0,
            "mean_missing_rate": round(float(rate_arr.mean()), 1),
            "max_missing_rate": round(float(rate_arr.max()), 1) if len(rate_arr) else 0.0,
        },
    }


def compute_respondent_cv(
    df: pd.DataFrame,
    statement_cols: list[str],
    *,
    id_column: str | None = None,
    scale: SummaryScale | None = None,
    min_valid: int = 3,
) -> dict[str, Any]:
    """
    Coefficient of variation (stdev / mean) per respondent across statement columns.
    Uses pre-imputation data; only valid in-scale ratings count.
    """
    scale = scale or SummaryScale(lo=1, hi=5, cant_say=6)
    cols = [c for c in statement_cols if c in df.columns]
    if df.empty or not cols:
        return {
            "points": [],
            "n_computed": 0,
            "n_skipped": 0,
            "n_total": 0,
            "min_valid": min_valid,
            "id_column": id_column or "",
            "stats": {},
        }

    ratings = np.column_stack([_column_ratings_array(df[c], scale) for c in cols])
    valid_count = np.sum(~np.isnan(ratings), axis=1)
    means = np.nanmean(ratings, axis=1)
    stds = np.nanstd(ratings, axis=1, ddof=0)

    with np.errstate(divide="ignore", invalid="ignore"):
        cv = stds / means

    points: list[dict[str, Any]] = []
    n_skipped = 0
    for i in range(len(df)):
        if valid_count[i] < min_valid or means[i] <= 0 or np.isnan(cv[i]):
            n_skipped += 1
            continue

        label = str(i + 1)
        if id_column and id_column in df.columns:
            raw_id = df.iloc[i][id_column]
            if not _is_nan_like(raw_id) and str(raw_id).strip() != "":
                label = str(raw_id).strip()

        points.append(
            {
                "index": i + 1,
                "label": label,
                "cv": round(float(cv[i]), 4),
            }
        )

    stats: dict[str, float] = {}
    if points:
        arr = np.array([p["cv"] for p in points], dtype=float)
        stats = {
            "mean": round(float(arr.mean()), 4),
            "min": round(float(arr.min()), 4),
            "max": round(float(arr.max()), 4),
        }

    return {
        "points": points,
        "n_computed": len(points),
        "n_skipped": n_skipped,
        "n_total": len(df),
        "min_valid": min_valid,
        "id_column": id_column or "",
        "stats": stats,
    }
