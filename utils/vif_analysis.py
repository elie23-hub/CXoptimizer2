"""
Variance Inflation Factor (VIF) checks for statement predictors.
Flags collinear groups that may cause multicollinearity in MLR.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

DEFAULT_VIF_THRESHOLD = 10.0
CORRELATION_CLUSTER_THRESHOLD = 0.85
SINGULAR_RANK_TOL = 1e-7


def _pairwise_dependence(
    x: np.ndarray,
    y: np.ndarray,
) -> tuple[bool, float]:
    """
    True when two predictors are collinear for MLR (with intercept).
    Detects identical or proportional columns — not affine shifts (y = x + c).
    """
    mask = ~(np.isnan(x) | np.isnan(y))
    xv = x[mask].astype(float)
    yv = y[mask].astype(float)
    if len(xv) < 3:
        return False, 0.0

    if np.allclose(xv, yv, rtol=SINGULAR_RANK_TOL, atol=SINGULAR_RANK_TOL):
        return True, 1.0

    x_std = float(np.std(xv, ddof=0))
    y_std = float(np.std(yv, ddof=0))
    if x_std == 0.0 and y_std == 0.0:
        return True, 1.0
    if x_std == 0.0 or y_std == 0.0:
        return False, 0.0

    r = abs(float(np.corrcoef(xv, yv)[0, 1]))

    # y = c * x (scalar multiple) — causes singular X'X with other predictors
    ratios = np.divide(
        yv,
        xv,
        out=np.full_like(yv, np.nan, dtype=float),
        where=np.abs(xv) > SINGULAR_RANK_TOL,
    )
    valid_ratios = ratios[~np.isnan(ratios)]
    if len(valid_ratios) == len(xv) and float(np.std(valid_ratios, ddof=0)) <= SINGULAR_RANK_TOL:
        return True, r

    return False, r


def _merge_pair_groups(pairs: list[tuple[str, str, float]]) -> list[list[str]]:
    """Merge pairs that share a variable only when all members are mutually dependent."""
    if not pairs:
        return []

    parent: dict[str, str] = {}

    def find(col: str) -> str:
        if col not in parent:
            parent[col] = col
        while parent[col] != col:
            parent[col] = parent[parent[col]]
            col = parent[col]
        return col

    def union(a: str, b: str) -> None:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    pair_set = {(a, b) for a, b, _ in pairs}
    pair_set |= {(b, a) for a, b, _ in pairs}

    for a, b, _ in pairs:
        union(a, b)

    clusters: dict[str, list[str]] = {}
    for col in parent:
        clusters.setdefault(find(col), []).append(col)

    merged: list[list[str]] = []
    for members in clusters.values():
        members = sorted(set(members))
        if len(members) < 2:
            continue
        # Keep cluster only if every pair inside is dependent (avoid transitive false joins).
        if all((members[i], members[j]) in pair_set for i in range(len(members)) for j in range(i + 1, len(members))):
            merged.append(members)
        else:
            for a, b, _ in pairs:
                if a in members and b in members:
                    pair_group = sorted([a, b])
                    if pair_group not in merged:
                        merged.append(pair_group)

    # Deduplicate while preserving order
    seen: set[tuple[str, ...]] = set()
    unique: list[list[str]] = []
    for group in sorted(merged, key=lambda g: (len(g), g)):
        key = tuple(group)
        if key not in seen:
            seen.add(key)
            unique.append(group)
    return unique


def _vif_values(X: np.ndarray) -> list[float]:
    """VIF per column: regress each predictor on all others."""
    _, p = X.shape
    vifs: list[float] = []
    for j in range(p):
        y = X[:, j]
        others = np.delete(X, j, axis=1)
        if others.shape[1] == 0:
            vifs.append(1.0)
            continue
        model = LinearRegression()
        model.fit(others, y)
        r2 = float(model.score(others, y))
        if r2 >= 1.0 - 1e-12:
            vifs.append(float("inf"))
        else:
            vifs.append(1.0 / (1.0 - r2))
    return vifs


def _cluster_collinear_groups(
    flagged_cols: list[str],
    corr: pd.DataFrame,
    vif_by_col: dict[str, float],
    label_map: dict[str, str],
) -> list[dict[str, Any]]:
    """Merge high-VIF variables into groups linked by strong pairwise correlation."""
    if not flagged_cols:
        return []

    parent = {col: col for col in flagged_cols}

    def find(col: str) -> str:
        while parent[col] != col:
            parent[col] = parent[parent[col]]
            col = parent[col]
        return col

    def union(a: str, b: str) -> None:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    for i, col_a in enumerate(flagged_cols):
        for col_b in flagged_cols[i + 1 :]:
            if abs(float(corr.loc[col_a, col_b])) >= CORRELATION_CLUSTER_THRESHOLD:
                union(col_a, col_b)

    clusters: dict[str, list[str]] = {}
    for col in flagged_cols:
        clusters.setdefault(find(col), []).append(col)

    groups: list[dict[str, Any]] = []
    for members in clusters.values():
        if len(members) < 2:
            continue

        members = sorted(
            members,
            key=lambda c: (vif_by_col.get(c) is None, -(vif_by_col.get(c) or 0)),
        )
        vifs = [vif_by_col[c] for c in members]
        max_vif = max(vifs)
        max_r = 0.0
        for i, col_a in enumerate(members):
            for col_b in members[i + 1 :]:
                max_r = max(max_r, abs(float(corr.loc[col_a, col_b])))

        keeper = min(
            members,
            key=lambda c: (
                vif_by_col.get(c) is None,
                float("inf") if np.isinf(vif_by_col.get(c, 0)) else vif_by_col.get(c, 0),
            ),
        )
        fix_members = [c for c in members if c != keeper]
        fix_members.sort(
            key=lambda c: (
                vif_by_col.get(c) is None,
                -(vif_by_col.get(c) or 0) if not np.isinf(vif_by_col.get(c, 0)) else float("-inf"),
            ),
        )

        fix_list: list[dict[str, Any]] = []
        for col in fix_members:
            vif = vif_by_col[col]
            r_keep = abs(float(corr.loc[col, keeper]))
            fix_list.append(
                {
                    "variable": col,
                    "label": label_map.get(col, ""),
                    "correlation": round(r_keep, 2),
                    "vif": None if np.isinf(vif) else round(float(vif), 1),
                    "vif_display": "∞" if np.isinf(vif) else str(round(float(vif), 1)),
                }
            )

        section_match = keeper.split("_", 1)
        section_id = section_match[0] if section_match else ""

        groups.append(
            {
                "section": section_id,
                "keep_variable": keeper,
                "keep_label": label_map.get(keeper, ""),
                "fix_list": fix_list,
                "max_vif": None if np.isinf(max_vif) else round(float(max_vif), 1),
                "max_vif_display": "∞" if np.isinf(max_vif) else str(round(float(max_vif), 1)),
                "correlation": round(max_r, 2),
            }
        )

    groups.sort(
        key=lambda item: (item["max_vif"] is None, item["max_vif"] or 0),
        reverse=True,
    )
    return groups


def compute_singular_matrix_groups(
    df: pd.DataFrame,
    statement_cols: list[str],
    label_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    """
    Find pairs (or minimal sets) of statement variables that are linearly dependent.
    Uses pairwise checks on overlapping non-missing rows — not listwise deletion.
    """
    label_map = label_map or {}
    result: dict[str, Any] = {
        "groups": [],
        "computed": False,
        "skip_reason": None,
        "is_singular": False,
    }

    if len(statement_cols) < 2:
        result["skip_reason"] = "Need at least 2 statements to check singularity."
        return result

    work = df[statement_cols].apply(pd.to_numeric, errors="coerce")
    if len(work) < 3:
        result["skip_reason"] = "Not enough rows for singularity check."
        return result

    arrays = {col: work[col].to_numpy(dtype=float) for col in statement_cols}
    constant_cols = [col for col, arr in arrays.items() if np.nanstd(arr) == 0.0]
    if constant_cols:
        result["skip_reason"] = (
            "Some statements have no variation: " + ", ".join(constant_cols[:5])
        )
        return result

    dependent_pairs: list[tuple[str, str, float]] = []
    for i, col_a in enumerate(statement_cols):
        for col_b in statement_cols[i + 1 :]:
            dependent, r = _pairwise_dependence(arrays[col_a], arrays[col_b])
            if dependent:
                dependent_pairs.append((col_a, col_b, r))

    # Overall design-matrix rank on rows complete for all statements (if enough rows).
    complete = work.dropna()
    if len(complete) >= len(statement_cols) + 2:
        X = complete.to_numpy(dtype=float)
        result["is_singular"] = int(np.linalg.matrix_rank(X, tol=SINGULAR_RANK_TOL)) < X.shape[1]
    else:
        result["is_singular"] = len(dependent_pairs) > 0

    clusters = _merge_pair_groups(dependent_pairs)
    pair_lookup = {
        (a, b): r
        for a, b, r in dependent_pairs
    }

    groups: list[dict[str, Any]] = []
    for members in clusters:
        max_r = 0.0
        for i, col_a in enumerate(members):
            for col_b in members[i + 1 :]:
                r = pair_lookup.get((col_a, col_b), pair_lookup.get((col_b, col_a), 0.0))
                max_r = max(max_r, r)

        groups.append(
            {
                "variables": members,
                "pair_count": max(0, len(members) - 1),
                "members": [
                    {"variable": col, "label": label_map.get(col, "")}
                    for col in members
                ],
                "max_correlation": round(max_r, 4),
            }
        )

    groups.sort(
        key=lambda item: (-len(item["variables"]), -item["max_correlation"]),
    )
    result["groups"] = groups
    result["computed"] = True
    result["pair_count"] = len(dependent_pairs)
    return result


def compute_statement_vif(
    df: pd.DataFrame,
    statement_cols: list[str],
    label_map: dict[str, str] | None = None,
    threshold: float = DEFAULT_VIF_THRESHOLD,
) -> dict[str, Any]:
    """
    Compute VIF and return collinear groups (variables to review together).
    """
    label_map = label_map or {}
    result: dict[str, Any] = {
        "threshold": threshold,
        "groups": [],
        "computed": False,
        "skip_reason": None,
    }

    if len(statement_cols) < 2:
        result["skip_reason"] = "Need at least 2 statements to compute VIF."
        return result

    work = df[statement_cols].apply(pd.to_numeric, errors="coerce")
    work = work.dropna()
    if len(work) < len(statement_cols) + 5:
        result["skip_reason"] = (
            f"Not enough complete rows for VIF ({len(work)} rows, "
            f"{len(statement_cols)} statements)."
        )
        return result

    X = work.to_numpy(dtype=float)
    col_std = X.std(axis=0, ddof=0)
    constant_cols = [statement_cols[i] for i, std in enumerate(col_std) if std == 0]
    if constant_cols:
        result["skip_reason"] = (
            "Some statements have no variation: " + ", ".join(constant_cols[:5])
        )
        return result

    try:
        vifs = _vif_values(X)
    except Exception as exc:
        result["skip_reason"] = f"VIF could not be computed: {exc}"
        return result

    vif_by_col = dict(zip(statement_cols, vifs))
    flagged_cols = [col for col, vif in vif_by_col.items() if vif > threshold]
    corr = work.corr()
    result["groups"] = _cluster_collinear_groups(flagged_cols, corr, vif_by_col, label_map)
    result["computed"] = True
    return result
