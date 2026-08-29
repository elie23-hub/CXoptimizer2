"""
Gap analysis: MLR importance, performance metrics, and bi-plot data.
Trains a fresh model on each compute request using the uploaded dataset.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from utils.data_loader import detect_statement_columns, group_sections

MetricKind = Literal["top2", "top3", "mean"]
ScaleKind = Literal["1-5", "1-10"]
QuadrantKind = Literal["urgent", "maintain", "overkill", "low"]


def fit_mlr_gradient_descent(
    X: np.ndarray,
    y: np.ndarray,
    *,
    learning_rate: float | None = None,
    max_iter: int = 2500,
    tol: float = 1e-9,
) -> dict[str, Any]:
    """
    Batch gradient descent for y ≈ intercept + X @ coef.

    Features are standardized for stable steps; coefficients are returned in
    the original feature scale. Loss history is MSE on the training set.
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).ravel()
    n, p = X.shape
    if n == 0 or p == 0:
        raise ValueError("Cannot train MLR with empty X.")

    x_mean = X.mean(axis=0)
    x_std = X.std(axis=0)
    x_std = np.where(x_std < 1e-12, 1.0, x_std)
    Xs = (X - x_mean) / x_std
    Xb = np.column_stack([np.ones(n), Xs])

    # Step size from a rough Lipschitz bound of ∇MSE ≈ (2/n)||X||²
    if learning_rate is None:
        xtx_frob = float(np.sum(Xb * Xb))
        learning_rate = min(0.5, 0.9 * n / max(xtx_frob, 1e-8))

    theta = np.zeros(p + 1, dtype=float)
    history: list[dict[str, float | int]] = []
    prev_loss: float | None = None
    converged = False
    stop_reason = "max_iterations"

    # Log sparsely for long runs so the UI stays light
    log_every = 1 if max_iter <= 400 else max(1, max_iter // 400)

    for i in range(1, max_iter + 1):
        resid = Xb @ theta - y
        loss = float(np.mean(resid ** 2))
        grad = (2.0 / n) * (Xb.T @ resid)
        theta -= learning_rate * grad

        if i == 1 or i == max_iter or i % log_every == 0 or (
            prev_loss is not None and abs(prev_loss - loss) < tol
        ):
            history.append({"iteration": i, "loss": round(loss, 8)})

        if prev_loss is not None and abs(prev_loss - loss) < tol:
            converged = True
            stop_reason = "loss_tol"
            if history[-1]["iteration"] != i:
                history.append({"iteration": i, "loss": round(loss, 8)})
            break
        prev_loss = loss

    intercept = float(theta[0] - np.sum(theta[1:] * x_mean / x_std))
    coefs = (theta[1:] / x_std).astype(float)

    return {
        "intercept": intercept,
        "coefficients": coefs,
        "history": history,
        "converged": converged,
        "iterations": int(history[-1]["iteration"]) if history else 0,
        "max_iter": max_iter,
        "learning_rate": float(learning_rate),
        "tol": tol,
        "final_loss": float(history[-1]["loss"]) if history else None,
        "initial_loss": float(history[0]["loss"]) if history else None,
        "stop_reason": stop_reason,
    }


def _predict_mlr(X: np.ndarray, intercept: float, coefs: np.ndarray) -> np.ndarray:
    return intercept + np.asarray(X, dtype=float) @ np.asarray(coefs, dtype=float)


@dataclass
class StatementResult:
    column: str
    section: int
    section_name: str
    label: str
    importance: float
    importance_pct: float
    importance_section_pct: float
    performance: float
    z_importance: float
    z_performance: float
    quadrant: QuadrantKind


def _scale_bounds(scale: ScaleKind) -> tuple[int, int]:
    if scale == "1-10":
        return 1, 10
    return 1, 5


def _top_box_threshold(scale: ScaleKind, boxes: int) -> int:
    _, hi = _scale_bounds(scale)
    return hi - boxes + 1


def performance_score(series: pd.Series, metric: MetricKind, scale: ScaleKind) -> float:
    """Performance for one statement as a percentage (0–100)."""
    lo, hi = _scale_bounds(scale)
    vals = pd.to_numeric(series, errors="coerce").dropna()
    vals = vals[(vals >= lo) & (vals <= hi)]
    if vals.empty:
        return 0.0

    if metric in ("mean", "weighted"):
        return float(vals.mean() / hi * 100)

    threshold = _top_box_threshold(scale, 2 if metric == "top2" else 3)
    return float((vals >= threshold).mean() * 100)


def _z_scores(values: list[float]) -> list[float]:
    arr = np.array(values, dtype=float)
    if len(arr) < 2:
        return [0.0] * len(arr)
    std = arr.std(ddof=0)
    if std == 0:
        return [0.0] * len(arr)
    mean = arr.mean()
    return ((arr - mean) / std).tolist()


def _quadrant(z_imp: float, z_perf: float) -> QuadrantKind:
    if z_imp >= 0 and z_perf < 0:
        return "urgent"
    if z_imp >= 0 and z_perf >= 0:
        return "maintain"
    if z_imp < 0 and z_perf >= 0:
        return "overkill"
    return "low"


def _display_label(column: str, question_labels: dict[str, str]) -> str:
    if column in question_labels and question_labels[column]:
        return question_labels[column]
    parts = column.split("_", 2)
    if len(parts) >= 3:
        return parts[2].strip(" .")
    return column


def _section_name(section: int, names: dict[str, str]) -> str:
    custom = names.get(str(section), "").strip()
    if custom:
        return custom
    return f"Section {section}"


def _sumproduct_csat(statements: list[StatementResult]) -> float:
    """Importance-weighted performance (SUMPRODUCT-style CSAT)."""
    if not statements:
        return 0.0
    weights = [r.importance_pct for r in statements]
    total_w = sum(weights)
    if total_w == 0:
        return 0.0
    return round(sum(r.performance * r.importance_pct for r in statements) / total_w, 1)


def _apply_section_importance(raw_results: list[StatementResult]) -> None:
    """Re-normalize global importance within each section to sum to 100%."""
    by_section: dict[int, list[StatementResult]] = {}
    for r in raw_results:
        by_section.setdefault(r.section, []).append(r)

    for rows in by_section.values():
        total = sum(r.importance_pct for r in rows) or 1.0
        for r in rows:
            r.importance_section_pct = round(r.importance_pct / total * 100, 1)


def _statement_payload(r: StatementResult) -> dict[str, Any]:
    return {
        "column": r.column,
        "section": r.section,
        "section_name": r.section_name,
        "label": r.label,
        "performance": r.performance,
        "importance": r.importance_pct,
        "importance_section": r.importance_section_pct,
        "quadrant": r.quadrant,
        "z_importance": r.z_importance,
        "z_performance": r.z_performance,
    }


def _build_table_sections(raw_results: list[StatementResult]) -> list[dict[str, Any]]:
    table_sections: list[dict[str, Any]] = []
    seen_sections: dict[int, list[StatementResult]] = {}
    for r in raw_results:
        seen_sections.setdefault(r.section, []).append(r)

    for sec in sorted(seen_sections):
        rows = seen_sections[sec]
        table_sections.append(
            {
                "section": sec,
                "section_name": rows[0].section_name if rows else f"Section {sec}",
                "statements": [
                    {
                        "column": r.column,
                        "label": r.label,
                        "performance": r.performance,
                        "importance": r.importance_pct,
                        "importance_section": r.importance_section_pct,
                        "quadrant": r.quadrant,
                        "z_importance": r.z_importance,
                        "z_performance": r.z_performance,
                    }
                    for r in rows
                ],
            }
        )
    return table_sections


def _model_quality_hint(model_r2: float) -> str:
    if model_r2 >= 0.70:
        return "Good / High (R² 0.70–1.00) — OSAT variance is explained well by the statements."
    if model_r2 >= 0.30:
        return "Normal / Moderate (R² 0.30–0.69) — usable, but other drivers may exist outside the model."
    return "Bad / Low (R² 0.00–0.29) — importance rankings may be unstable; review predictors and data quality."


def _prepare_work_df(
    df: pd.DataFrame,
    osat_column: str,
    stmt_cols: list[str],
    lo: int,
    hi: int,
) -> pd.DataFrame:
    """Keep rows with valid OSAT and in-scale statement ratings."""
    work = df[[osat_column] + stmt_cols].copy()
    for col in [osat_column] + stmt_cols:
        work[col] = pd.to_numeric(work[col], errors="coerce")

    work = work.dropna(subset=[osat_column])
    work = work[(work[osat_column] >= lo) & (work[osat_column] <= hi)]

    stmt = work[stmt_cols]
    work[stmt_cols] = stmt.where((stmt >= lo) & (stmt <= hi))
    work = work.dropna(subset=stmt_cols)
    return work


def _rmse_good_threshold(scale: ScaleKind) -> float:
    """Green bar: test RMSE within 25% of the OSAT scale width (mirrors R² 0.5 spirit)."""
    lo, hi = _scale_bounds(scale)
    return round((hi - lo) * 0.25, 2)


def run_gap_analysis(
    df: pd.DataFrame,
    osat_column: str,
    scale: ScaleKind,
    metric: MetricKind,
    section_names: dict[str, str] | None = None,
    question_labels: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """
    Train MLR on uploaded data, compute importance & performance, return bi-plot payload.
    """
    section_names = section_names or {}
    label_map = {
        item.get("variable", ""): item.get("label", "")
        for item in (question_labels or [])
        if item.get("variable")
    }

    statements = detect_statement_columns(list(df.columns))
    if not statements:
        raise ValueError("No statement columns (S#_Q#) found in uploaded data.")
    if not osat_column or osat_column not in df.columns:
        raise ValueError("Overall satisfaction (OSAT) column not found.")

    stmt_cols = [s.column for s in statements]
    lo, hi = _scale_bounds(scale)

    work = _prepare_work_df(df, osat_column, stmt_cols, lo, hi)

    if len(work) < 10:
        raise ValueError("Not enough valid responses to train the model (need at least 10).")

    X = work[stmt_cols].values
    y = work[osat_column].values.astype(float)
    n_respondents = len(y)
    n_predictors = len(stmt_cols)

    # 70% train — used for importance coefficients (as before).
    X_train, X_hold, y_train, y_hold = train_test_split(
        X, y, test_size=0.30, random_state=42
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_hold, y_hold, test_size=1 / 3, random_state=42
    )

    train_fit = fit_mlr_gradient_descent(X_train, y_train)
    intercept = float(train_fit["intercept"])
    coefs = np.asarray(train_fit["coefficients"], dtype=float)

    y_train_pred = _predict_mlr(X_train, intercept, coefs)
    y_val_pred = _predict_mlr(X_val, intercept, coefs) if len(y_val) else np.array([])
    y_test_pred = _predict_mlr(X_test, intercept, coefs) if len(y_test) else np.array([])

    train_r2 = float(r2_score(y_train, y_train_pred))
    val_r2 = float(r2_score(y_val, y_val_pred)) if len(y_val) else train_r2
    test_r2 = float(r2_score(y_test, y_test_pred)) if len(y_test) else val_r2

    n_train, n_val, n_test = len(y_train), len(y_val), len(y_test)

    train_rmse = float(np.sqrt(mean_squared_error(y_train, y_train_pred)))
    val_rmse = float(np.sqrt(mean_squared_error(y_val, y_val_pred))) if len(y_val) else None
    val_mae = float(mean_absolute_error(y_val, y_val_pred)) if len(y_val) else None
    test_rmse = float(np.sqrt(mean_squared_error(y_test, y_test_pred))) if len(y_test) else None
    test_mae = float(mean_absolute_error(y_test, y_test_pred)) if len(y_test) else None

    coefs_list = coefs.tolist()
    abs_sum = sum(abs(c) for c in coefs_list) or 1.0

    sections = group_sections(statements)

    raw_results: list[StatementResult] = []
    for stmt, coef in zip(statements, coefs_list):
        perf = performance_score(work[stmt.column], metric, scale)
        imp_pct = abs(coef) / abs_sum * 100
        raw_results.append(
            StatementResult(
                column=stmt.column,
                section=stmt.section,
                section_name=_section_name(stmt.section, section_names),
                label=_display_label(stmt.column, label_map),
                importance=float(coef),
                importance_pct=round(imp_pct, 1),
                importance_section_pct=0.0,
                performance=round(perf, 1),
                z_importance=0.0,
                z_performance=0.0,
                quadrant="low",
            )
        )

    _apply_section_importance(raw_results)

    z_imps = _z_scores([r.importance for r in raw_results])
    z_perfs = _z_scores([r.performance for r in raw_results])
    for r, zi, zp in zip(raw_results, z_imps, z_perfs):
        r.z_importance = round(zi, 3)
        r.z_performance = round(zp, 3)
        r.quadrant = _quadrant(zi, zp)

    urgent = [r for r in raw_results if r.quadrant == "urgent"]
    urgent.sort(key=lambda r: (r.performance, -r.importance_pct))

    overall_csat = _sumproduct_csat(raw_results)
    all_statements = [_statement_payload(r) for r in raw_results]
    table_sections = _build_table_sections(raw_results)

    metric_labels = {
        "top2": "top-2-box",
        "top3": "top-3-box",
        "mean": "mean",
        "weighted": "mean",
    }

    return {
        "summary_all": {
            "sections": len(sections),
            "statements": len(statements),
            "overall_csat": overall_csat,
            "fix_urgently": len(urgent),
            "respondents": len(work),
        },
        "statements": all_statements,
        "sections_catalog": [
            {
                "id": str(sec.section),
                "name": _section_name(sec.section, section_names),
                "count": sec.count,
            }
            for sec in sections
        ],
        "model": {
            "train_r2": round(train_r2, 4),
            "test_r2": round(test_r2, 4),
            "train_rmse": round(train_rmse, 3),
            "val_rmse": round(val_rmse, 3) if val_rmse is not None else None,
            "val_mae": round(val_mae, 3) if val_mae is not None else None,
            "test_rmse": round(test_rmse, 3) if test_rmse is not None else None,
            "test_mae": round(test_mae, 3) if test_mae is not None else None,
            "test_rmse_threshold": _rmse_good_threshold(scale),
            "intercept": round(intercept, 4),
            "coefficients": {
                col: round(float(c), 6) for col, c in zip(stmt_cols, coefs_list)
            },
            "mean_ratings": {
                col: round(float(work[col].mean()), 4) for col in stmt_cols
            },
            "n_respondents": n_respondents,
            "n_train": n_train,
            "n_val": n_val,
            "n_test": n_test,
            "n_predictors": n_predictors,
            "split_label": "70% train · 20% validation · 10% test",
            "importance_split": "70% training data",
            "quality_hint": _model_quality_hint(train_r2),
            "model_version": 7,
            "optimizer": "batch_gradient_descent",
            "converged": bool(train_fit["converged"]),
            "gd": {
                "iterations": train_fit["iterations"],
                "max_iter": train_fit["max_iter"],
                "learning_rate": round(float(train_fit["learning_rate"]), 6),
                "tol": train_fit["tol"],
                "initial_loss": train_fit["initial_loss"],
                "final_loss": train_fit["final_loss"],
                "stop_reason": train_fit["stop_reason"],
                "history": train_fit["history"],
            },
        },
        "metric_label": metric_labels.get(metric, metric),
        "scale": scale,
        "biplot": [
            {
                "column": s["column"],
                "label": s["label"],
                "section": s["section"],
                "section_name": s["section_name"],
                "z_importance": s["z_importance"],
                "z_performance": s["z_performance"],
                "performance": s["performance"],
                "importance": s["importance"],
                "quadrant": s["quadrant"],
            }
            for s in all_statements
        ],
        "priority_actions": [
            {
                "label": r.label,
                "subtitle": f"high importance · {r.performance:.0f}% satisfied",
            }
            for r in urgent
        ],
        "table": {
            "overall_csat": overall_csat,
            "sections": table_sections,
        },
        # Legacy shape for older cached sessions
        "summary": {
            "sections": len(sections),
            "statements": len(statements),
            "overall_performance": overall_csat,
            "fix_urgently": len(urgent),
            "respondents": len(work),
        },
    }
