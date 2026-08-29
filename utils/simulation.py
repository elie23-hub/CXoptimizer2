"""
Simulation engine — bottom-up, top-down, and optimal (simplex LP).

Formula (shared):
  OSAT = Σ (performanceᵢ × reduced_importanceᵢ) / 100

Bottom-up: user sets performances → OSAT.
Top-down: user sets target OSAT → heuristic score combinations.
Optimal: user sets target OSAT → simplex LP (prioritize high-importance drivers).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import linprog

from utils.gap_analysis import MetricKind, ScaleKind


def compute_reduced_importance(statements: list[dict[str, Any]]) -> list[float]:
    """
    Normalize statement importance weights so they sum to 100%.

    Prefers stored ``reduced_importance`` when every row has it; otherwise
    normalizes from ``importance``.
    """
    if not statements:
        return []

    if all(s.get("reduced_importance") is not None for s in statements):
        raw = [float(s["reduced_importance"]) for s in statements]
    else:
        raw = [float(s.get("importance", 0)) for s in statements]

    total = sum(raw)
    if total <= 0:
        share = 100.0 / len(statements) if statements else 0.0
        return [round(share, 4) for _ in statements]

    return [round(w / total * 100.0, 4) for w in raw]


def attach_reduced_importance(statements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return statement copies with global and section reduced importance filled in."""
    global_weights = compute_reduced_importance(statements)
    enriched: list[dict[str, Any]] = []
    for stmt, weight in zip(statements, global_weights):
        row = dict(stmt)
        row["reduced_importance"] = weight
        enriched.append(row)

    by_section: dict[Any, list[dict[str, Any]]] = {}
    for row in enriched:
        by_section.setdefault(row.get("section"), []).append(row)

    for rows in by_section.values():
        section_weights = compute_reduced_importance_section(rows)
        for row, weight in zip(rows, section_weights):
            row["reduced_importance_section"] = weight

    return enriched


def compute_reduced_importance_section(statements: list[dict[str, Any]]) -> list[float]:
    """Normalize section-level importance weights to sum to 100%."""
    if not statements:
        return []

    if all(s.get("reduced_importance_section") is not None for s in statements):
        raw = [float(s["reduced_importance_section"]) for s in statements]
    elif all(s.get("importance_section") is not None for s in statements):
        raw = [float(s["importance_section"]) for s in statements]
    else:
        raw = [float(s.get("importance", 0)) for s in statements]

    total = sum(raw)
    if total <= 0:
        share = 100.0 / len(statements) if statements else 0.0
        return [round(share, 4) for _ in statements]

    return [round(w / total * 100.0, 4) for w in raw]


def section_weighted_csat(
    statements: list[dict[str, Any]],
    *,
    perf_key: str = "performance",
) -> float:
    """Section CSAT = Σ(performance × reduced section importance) / 100."""
    if not statements:
        return 0.0

    weights = compute_reduced_importance_section(statements)
    total = sum(
        float(s.get(perf_key, s["performance"])) * weight
        for s, weight in zip(statements, weights)
    )
    return round(total / 100.0, 1)


def weighted_osat(
    statements: list[dict[str, Any]],
    *,
    perf_key: str = "performance",
) -> float:
    """
    OSAT = Σ (performance × reduced importance), weights sum to 100%.

    Performance is stored as 0–100%; dividing by 100 yields 0–100% overall.
    """
    if not statements:
        return 0.0

    weights = compute_reduced_importance(statements)
    total = sum(
        float(s.get(perf_key, s["performance"])) * weight
        for s, weight in zip(statements, weights)
    )
    return round(total / 100.0, 1)


def _gap_overall_csat(gap_result: dict[str, Any]) -> float | None:
    """Overall CSAT from gap analysis (SUMPRODUCT of performance × importance)."""
    for key in ("summary_all", "table", "summary"):
        block = gap_result.get(key) or {}
        val = block.get("overall_csat")
        if val is None:
            val = block.get("overall_performance")
        if val is not None:
            return round(float(val), 1)
    return None


def build_simulation_snapshot(
    gap_result: dict[str, Any],
    *,
    scale: ScaleKind,
    metric: MetricKind,
    filename: str = "",
) -> dict[str, Any]:
    """Build JSON: one row per statement with performance % and reduced importance."""
    model = gap_result.get("model") or {}
    raw_coefs: dict[str, float] = {
        k: float(v) for k, v in (model.get("coefficients") or {}).items()
    }

    statements: list[dict[str, Any]] = []
    for s in gap_result.get("statements") or []:
        col = s["column"]
        raw_beta = raw_coefs.get(col, 0.0)
        statements.append(
            {
                "column": col,
                "label": s["label"],
                "section": s.get("section"),
                "section_name": s.get("section_name", ""),
                "performance": float(s["performance"]),
                "importance": float(s["importance"]),
                "importance_section": float(s.get("importance_section", 0)),
                "quadrant": s.get("quadrant") or "low",
                "z_importance": (
                    float(s["z_importance"])
                    if s.get("z_importance") is not None
                    else None
                ),
                "z_performance": (
                    float(s["z_performance"])
                    if s.get("z_performance") is not None
                    else None
                ),
                "mlr_beta": round(raw_beta, 6),
            }
        )

    statements = attach_reduced_importance(statements)

    baseline_overall = _gap_overall_csat(gap_result)
    if baseline_overall is None:
        baseline_overall = weighted_osat(statements)

    perfs = [float(s["performance"]) for s in statements]
    perf_mean, perf_std = (
        (float(np.mean(perfs)), float(np.std(perfs, ddof=0)))
        if len(perfs) > 1
        else (float(perfs[0]) if perfs else 0.0, 0.0)
    )
    betas = [
        float(s["mlr_beta"]) if s.get("mlr_beta") is not None else 0.0
        for s in statements
    ]
    imp_mean, imp_std = (
        (float(np.mean(betas)), float(np.std(betas, ddof=0)))
        if len(betas) > 1
        else (float(betas[0]) if betas else 0.0, 0.0)
    )

    return {
        "version": 4,
        "filename": filename,
        "scale": scale,
        "metric": metric,
        "metric_label": gap_result.get("metric_label", metric),
        "baseline_overall": baseline_overall,
        "baseline_method": "sumproduct_reduced_importance",
        "statements": statements,
        "biplot_scale": {
            "performance_mean": round(perf_mean, 6),
            "performance_std": round(perf_std, 6),
            "importance_mean": round(imp_mean, 6),
            "importance_std": round(imp_std, 6),
            "importance_basis": "mlr_beta",
        },
        "model": {
            "type": "sumproduct",
            "train_r2": model.get("train_r2"),
            "formula": "OSAT = Σ(performance × reduced importance)",
        },
    }


def apply_simulated_scores(
    snapshot: dict[str, Any],
    scores: dict[str, float],
) -> list[dict[str, Any]]:
    """Merge user slider values (performance %) into statement rows."""
    merged = []
    for s in snapshot.get("statements") or []:
        col = s["column"]
        sim = scores.get(col, s["performance"])
        sim = max(0.0, min(100.0, float(sim)))
        merged.append({**s, "simulated_performance": round(sim, 1)})
    return merged


def predict_bottom_up(
    snapshot: dict[str, Any],
    scores: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Bottom-up weighted OSAT from simulated performance scores.

    OSAT = Σ (performanceᵢ × reduced_importanceᵢ) / 100
    """
    statements = list(snapshot.get("statements") or [])
    if not statements:
        raise ValueError("Simulation data has no statements. Re-run gap analysis.")

    if scores:
        statements = apply_simulated_scores(snapshot, scores)

    stored_baseline = snapshot.get("baseline_overall")
    if stored_baseline is not None:
        baseline = round(float(stored_baseline), 1)
    else:
        baseline = weighted_osat(statements, perf_key="performance")

    predicted = weighted_osat(statements, perf_key="simulated_performance")
    delta = round(predicted - baseline, 1)

    return {
        "baseline_overall": baseline,
        "baseline_method": snapshot.get(
            "baseline_method", "sumproduct_reduced_importance"
        ),
        "predicted_overall": predicted,
        "delta_pts": delta,
        "method": "sumproduct_reduced_importance",
        "statements": statements,
    }


def _statement_weights_and_base(
    statements: list[dict[str, Any]],
) -> tuple[
    list[str],
    list[str],
    list[Any],
    list[str],
    list[float],
    list[float],
    list[str],
]:
    weights = compute_reduced_importance(statements)
    cols = [str(s["column"]) for s in statements]
    labels = [str(s.get("label") or s["column"]) for s in statements]
    sections = [s.get("section") for s in statements]
    section_names = [
        str(s.get("section_name") or (
            f"Section {s.get('section')}" if s.get("section") is not None else "Other"
        ))
        for s in statements
    ]
    base = [float(s.get("performance", 0)) for s in statements]
    quadrants = [str(s.get("quadrant") or "low") for s in statements]
    return cols, labels, sections, section_names, weights, base, quadrants


def _redistribute_delta(
    base: list[float],
    weights: list[float],
    delta_sum: float,
    *,
    mode: str = "importance",
    order: list[int] | None = None,
    allowed: list[int] | None = None,
) -> list[float]:
    """Adjust performances so Σ(p × w) changes by delta_sum (p clipped to 0–100)."""
    n = len(base)
    result = [max(0.0, min(100.0, float(p))) for p in base]
    remaining = float(delta_sum)
    allowed_set = set(allowed) if allowed is not None else set(range(n))
    indices = list(order) if order is not None else list(range(n))
    indices = [i for i in indices if i in allowed_set]

    def free_list() -> list[int]:
        out: list[int] = []
        for i in indices:
            if remaining > 0 and result[i] < 100.0 - 1e-9:
                out.append(i)
            elif remaining < 0 and result[i] > 1e-9:
                out.append(i)
        return out

    if not indices:
        return [round(p, 1) for p in result]

    if mode == "sequential":
        for i in indices:
            if abs(remaining) < 1e-6:
                break
            w = weights[i] if weights[i] > 1e-12 else 1e-12
            if remaining > 0:
                room = 100.0 - result[i]
                if room <= 1e-9:
                    continue
                dp = min(room, remaining / w)
            else:
                room = result[i]
                if room <= 1e-9:
                    continue
                dp = max(-room, remaining / w)
            result[i] = result[i] + dp
            remaining -= dp * w
        return [round(p, 1) for p in result]

    for _ in range(n + 6):
        movable = free_list()
        if abs(remaining) < 1e-6 or not movable:
            break
        before = {i: result[i] for i in movable}
        if mode == "equal_points":
            w_sum = sum(weights[i] for i in movable) or 1.0
            dp = remaining / w_sum
            for i in movable:
                result[i] = max(0.0, min(100.0, result[i] + dp))
        else:
            denom = sum(weights[i] ** 2 for i in movable) or 1.0
            for i in movable:
                dp = remaining * weights[i] / denom
                result[i] = max(0.0, min(100.0, result[i] + dp))
        applied = sum((result[i] - before[i]) * weights[i] for i in movable)
        if abs(applied) < 1e-9:
            break
        remaining -= applied

    return [round(p, 1) for p in result]


VALID_QUADRANTS = ("urgent", "maintain", "overkill", "low")


def _normalize_quadrants(quadrants: list[str] | None) -> list[str]:
    """Selected gap-analysis quadrants allowed to change (empty = none)."""
    if not quadrants:
        return []
    out: list[str] = []
    for q in quadrants:
        key = str(q).strip().lower()
        if key in VALID_QUADRANTS and key not in out:
            out.append(key)
    return out


def _quadrant_label(q: str) -> str:
    return {
        "urgent": "Low performance high importance",
        "maintain": "High performance high importance",
        "overkill": "High performance low importance",
        "low": "Low performance low importance",
    }.get(q, q)


def _classify_quadrant(z_imp: float, z_perf: float) -> str:
    if z_imp >= 0 and z_perf < 0:
        return "urgent"
    if z_imp >= 0 and z_perf >= 0:
        return "maintain"
    if z_imp < 0 and z_perf >= 0:
        return "overkill"
    return "low"


def _z_score(value: float, mean: float, std: float) -> float:
    if abs(std) < 1e-12:
        return 0.0
    return round((float(value) - mean) / std, 4)


def _population_mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    arr = np.asarray(values, dtype=float)
    if len(arr) < 2:
        return float(arr.mean()), 0.0
    return float(arr.mean()), float(arr.std(ddof=0))


def _importance_axis_values(statements: list[dict[str, Any]]) -> list[float]:
    """
    Raw MLR coefficients for the biplot Y-axis — same basis as gap analysis.

    Gap analysis z-scores signed betas, not importance percentages. Percentages
    use abs(beta), which can place statements in the wrong half-plane.
    """
    vals: list[float] = []
    for s in statements:
        beta = _read_optional_float(s, "mlr_beta")
        if beta is None:
            beta = _read_optional_float(s, "importance") or 0.0
        vals.append(float(beta))
    return vals


def _perf_z_scale(snapshot: dict[str, Any], statements: list[dict[str, Any]]) -> tuple[float, float]:
    scale = snapshot.get("biplot_scale") or {}
    mean = scale.get("performance_mean")
    std = scale.get("performance_std")
    if mean is not None and std is not None:
        return float(mean), float(std)
    return _population_mean_std([float(s.get("performance", 0)) for s in statements])


def _imp_z_scale(snapshot: dict[str, Any], statements: list[dict[str, Any]]) -> tuple[float, float]:
    scale = snapshot.get("biplot_scale") or {}
    mean = scale.get("importance_mean")
    std = scale.get("importance_std")
    # Only trust stored scale when it was computed from MLR betas (v4+).
    if (
        mean is not None
        and std is not None
        and scale.get("importance_basis") == "mlr_beta"
    ):
        return float(mean), float(std)
    return _population_mean_std(_importance_axis_values(statements))


def _read_optional_float(row: dict[str, Any], key: str) -> float | None:
    if key not in row or row[key] is None:
        return None
    try:
        return float(row[key])
    except (TypeError, ValueError):
        return None


def enrich_statements_for_biplot(
    snapshot: dict[str, Any],
    statements: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Fill missing z_importance / z_performance / quadrant.

    Matches gap analysis: z_importance from signed MLR betas, z_performance
    from performance %.
    """
    rows = list(statements if statements is not None else snapshot.get("statements") or [])
    mean_p, std_p = _perf_z_scale(snapshot, rows)
    mean_i, std_i = _imp_z_scale(snapshot, rows)
    axis_vals = _importance_axis_values(rows)
    enriched: list[dict[str, Any]] = []
    for s, axis_val in zip(rows, axis_vals):
        row = dict(s)
        baseline = float(row.get("performance", 0))
        zi = _read_optional_float(row, "z_importance")
        zp = _read_optional_float(row, "z_performance")
        if zi is None:
            zi = _z_score(axis_val, mean_i, std_i)
        if zp is None:
            zp = _z_score(baseline, mean_p, std_p)
        row["z_importance"] = round(float(zi), 4)
        row["z_performance"] = round(float(zp), 4)
        # Always re-derive quadrant from z-scores so legacy wrong tags are fixed.
        row["quadrant"] = _classify_quadrant(row["z_importance"], row["z_performance"])
        enriched.append(row)
    return enriched


def _z_performance(perf: float, mean: float, std: float) -> float:
    return _z_score(perf, mean, std)


def build_biplot_points(
    snapshot: dict[str, Any],
    *,
    scores_by_col: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """
    Importance–performance biplot points.

    z_importance matches gap analysis (MLR beta z-scores) and stays fixed;
    z_performance updates from required/simulated performances on the x-axis.
    """
    statements = enrich_statements_for_biplot(snapshot)
    mean_p, std_p = _perf_z_scale(snapshot, statements)
    points: list[dict[str, Any]] = []
    for s in statements:
        col = str(s["column"])
        baseline = float(s.get("performance", 0))
        perf = float((scores_by_col or {}).get(col, baseline))
        zi = float(s["z_importance"])
        zp0 = float(s["z_performance"])
        zp1 = _z_performance(perf, mean_p, std_p)
        q0 = _classify_quadrant(zi, zp0)
        q1 = _classify_quadrant(zi, zp1)
        changed = abs(perf - baseline) >= 0.05
        points.append(
            {
                "column": col,
                "label": s.get("label") or col,
                "section": s.get("section"),
                "section_name": s.get("section_name", ""),
                "importance": float(s.get("importance", 0)),
                "performance": round(baseline, 1),
                "required_performance": round(perf, 1),
                "z_importance": round(zi, 4),
                "z_performance": zp1,
                "z_performance_baseline": round(zp0, 4),
                "quadrant": q1,
                "quadrant_baseline": q0,
                "changed": changed,
                "delta_pts": round(perf - baseline, 1),
            }
        )
    return points


def _option_payload(
    *,
    option_id: str,
    title: str,
    cols: list[str],
    labels: list[str],
    sections: list[Any],
    section_names: list[str],
    quadrants: list[str],
    base: list[float],
    weights: list[float],
    scores: list[float],
    target: float,
    baseline: float,
    allowed: set[int] | None = None,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    achieved = round(sum(p * w for p, w in zip(scores, weights)) / 100.0, 1)
    allowed_set = allowed if allowed is not None else set(range(len(base)))
    rows = []
    for i, (col, label, section, section_name, p0, p1, w, q) in enumerate(
        zip(cols, labels, sections, section_names, base, scores, weights, quadrants)
    ):
        changed = abs(p1 - p0) >= 0.05
        rows.append(
            {
                "column": col,
                "label": label,
                "section": section,
                "section_name": section_name,
                "quadrant": q,
                "performance": round(p0, 1),
                "required_performance": round(p1, 1),
                "reduced_importance": round(w, 4),
                "changed": changed,
                "delta_pts": round(p1 - p0, 1),
                "eligible": i in allowed_set,
            }
        )
    scores_by_col = {c: p for c, p in zip(cols, scores)}
    biplot = build_biplot_points(snapshot or {}, scores_by_col=scores_by_col)
    return {
        "id": option_id,
        "title": title,
        "achieved_overall": achieved,
        "target_overall": round(target, 1),
        "baseline_overall": round(baseline, 1),
        "feasible": abs(achieved - target) <= 0.55,
        "statements": rows,
        "biplot": biplot,
    }


def solve_top_down(
    snapshot: dict[str, Any],
    target_overall: float,
    *,
    option_index: int = 0,
    quadrants: list[str] | None = None,
) -> dict[str, Any]:
    """
    Invert OSAT = Σ(performance × reduced importance) / 100 for performance scores.

    Only statements in the selected gap-analysis quadrant(s) may change.
    Others stay fixed; some eligible statements may still not move when not needed.
    """
    statements = enrich_statements_for_biplot(snapshot)
    if not statements:
        raise ValueError("Simulation data has no statements. Re-run gap analysis.")

    (
        cols,
        labels,
        sections,
        section_names,
        weights,
        base,
        stmt_quadrants,
    ) = _statement_weights_and_base(statements)

    selected = _normalize_quadrants(quadrants)
    allowed = [i for i, q in enumerate(stmt_quadrants) if q in selected]

    if snapshot.get("baseline_overall") is not None:
        baseline = float(snapshot["baseline_overall"])
    else:
        baseline = weighted_osat(statements)

    target = max(0.0, min(100.0, float(target_overall)))
    current_sum = sum(p * w for p, w in zip(base, weights))
    delta_sum = target * 100.0 - current_sum

    n = len(base)
    allowed_set = set(allowed)
    by_importance = sorted(allowed, key=lambda i: (-weights[i], base[i], cols[i]))
    by_lowest_perf = sorted(allowed, key=lambda i: (base[i], -weights[i], cols[i]))
    by_room = sorted(
        allowed,
        key=lambda i: (
            -(100.0 - base[i]) * weights[i]
            if target >= baseline
            else -(base[i] * weights[i]),
            -weights[i],
            cols[i],
        ),
    )

    option_specs = [
        (
            "importance",
            "Priority by importance",
            lambda: _redistribute_delta(
                base,
                weights,
                delta_sum,
                mode="importance",
                order=list(range(n)),
                allowed=allowed,
            ),
        ),
        (
            "lowest_first",
            "Lift lowest scores first",
            lambda: _redistribute_delta(
                base,
                weights,
                delta_sum,
                mode="sequential",
                order=by_lowest_perf,
                allowed=allowed,
            ),
        ),
        (
            "focus_importance",
            "Focus on most important first",
            lambda: _redistribute_delta(
                base,
                weights,
                delta_sum,
                mode="sequential",
                order=by_importance,
                allowed=allowed,
            ),
        ),
        (
            "headroom",
            "Use statements with most room",
            lambda: _redistribute_delta(
                base,
                weights,
                delta_sum,
                mode="sequential",
                order=by_room,
                allowed=allowed,
            ),
        ),
        (
            "equal_points",
            "Share the change evenly",
            lambda: _redistribute_delta(
                base,
                weights,
                delta_sum,
                mode="equal_points",
                order=list(range(n)),
                allowed=allowed,
            ),
        ),
    ]

    options = [
        _option_payload(
            option_id=oid,
            title=title,
            cols=cols,
            labels=labels,
            sections=sections,
            section_names=section_names,
            quadrants=stmt_quadrants,
            base=base,
            weights=weights,
            scores=builder(),
            target=target,
            baseline=baseline,
            allowed=allowed_set,
            snapshot=snapshot,
        )
        for oid, title, builder in option_specs
    ]

    unique: list[dict[str, Any]] = []
    seen: set[tuple[float, ...]] = set()
    for opt in options:
        key = tuple(s["required_performance"] for s in opt["statements"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(opt)

    if not unique:
        unique = options[:1]

    idx = int(option_index) % len(unique)
    chosen = unique[idx]
    feasible = bool(chosen.get("feasible", True)) and bool(allowed)

    eligible_count = len(allowed)
    changed_count = sum(1 for s in chosen["statements"] if s.get("changed"))

    # Statements outside the selected quadrant(s) keep their baseline score but
    # still carry their weight in OSAT = Σ(performance × reduced importance), so
    # they cap how far the target can move in either direction.
    locked_sum = sum(
        base[i] * weights[i] for i in range(n) if i not in allowed_set
    )
    allowed_weight = sum(weights[i] for i in allowed)
    max_reachable = round((locked_sum + 100.0 * allowed_weight) / 100.0, 1)
    min_reachable = round(locked_sum / 100.0, 1)
    locked_contribution = round(locked_sum / 100.0, 1)
    locked_count = n - eligible_count

    if not selected:
        note_parts = [
            "No quadrant selected — showing original gap-analysis positions; "
            "scores stay at baseline."
        ]
    else:
        note_parts = [
            f"Only statements in selected quadrant(s) may change: "
            + ", ".join(_quadrant_label(q) for q in selected)
            + f" ({eligible_count} eligible)."
        ]
        if locked_count:
            note_parts.append(
                f"The other {locked_count} statement(s) stay at their current "
                f"scores but still count in OSAT = Σ(performance × reduced "
                f"importance), contributing {locked_contribution} pts. That "
                f"caps the reachable range at "
                f"{min_reachable}%–{max_reachable}%."
            )
        if not allowed:
            note_parts.append(
                "No statements fall in the selected quadrant(s), so scores stay at baseline."
            )
        elif not feasible:
            note_parts.append(
                f"Target {round(target, 1)}% is therefore not reachable — even with "
                f"every eligible statement at 100%, the overall reaches "
                f"{chosen['achieved_overall']}%."
            )
        elif changed_count < eligible_count:
            note_parts.append(
                "Some eligible statements stayed unchanged because moving them "
                "was not needed (or not useful) for this target."
            )

    return {
        "baseline_overall": round(baseline, 1),
        "target_overall": round(target, 1),
        "achieved_overall": chosen["achieved_overall"],
        "min_overall": min_reachable,
        "max_overall": max_reachable,
        "min_reachable_overall": min_reachable,
        "max_reachable_overall": max_reachable,
        "locked_contribution_pts": locked_contribution,
        "locked_count": locked_count,
        "feasible": feasible,
        "quadrants": selected,
        "eligible_count": eligible_count,
        "changed_count": changed_count,
        "option_index": idx,
        "option_count": len(unique),
        "option": chosen,
        "biplot": chosen.get("biplot") or [],
        "note": " ".join(note_parts),
        "options_summary": [
            {
                "id": o["id"],
                "title": o["title"],
                "achieved_overall": o["achieved_overall"],
                "feasible": o.get("feasible", True),
            }
            for o in unique
        ],
        "method": "sumproduct_reduced_importance",
        "formula": "OSAT = Σ(performance × reduced importance) / 100",
    }


def _inverse_statement_rows(
    *,
    cols: list[str],
    labels: list[str],
    sections: list[Any],
    section_names: list[str],
    base: list[float],
    weights: list[float],
    scores: list[float],
) -> list[dict[str, Any]]:
    rows = []
    for col, label, section, section_name, p0, p1, w in zip(
        cols, labels, sections, section_names, base, scores, weights
    ):
        changed = abs(p1 - p0) >= 0.05
        rows.append(
            {
                "column": col,
                "label": label,
                "section": section,
                "section_name": section_name,
                "performance": round(p0, 1),
                "required_performance": round(p1, 1),
                "reduced_importance": round(w, 4),
                "changed": changed,
                "delta_pts": round(p1 - p0, 1),
            }
        )
    return rows


def solve_optimal(
    snapshot: dict[str, Any],
    target_overall: float,
) -> dict[str, Any]:
    """
    Optimal inverse solve via linear programming (revised simplex).

    Minimize Σ (|Δperformanceᵢ| / reduced_importanceᵢ) subject to:
      Σ (performanceᵢ × reduced_importanceᵢ) = target × 100
      0 ≤ performanceᵢ ≤ 100

    Lower cost on high-importance statements steers change toward the
    highest-impact drivers first.
    """
    statements = list(snapshot.get("statements") or [])
    if not statements:
        raise ValueError("Simulation data has no statements. Re-run gap analysis.")

    (
        cols,
        labels,
        sections,
        section_names,
        weights,
        base,
        _stmt_quadrants,
    ) = _statement_weights_and_base(statements)
    if snapshot.get("baseline_overall") is not None:
        baseline = float(snapshot["baseline_overall"])
    else:
        baseline = weighted_osat(statements)

    target = max(0.0, min(100.0, float(target_overall)))
    n = len(base)
    w = np.asarray(weights, dtype=float)
    b = np.asarray(base, dtype=float)

    if n == 0:
        raise ValueError("No statements available for optimal solve.")

    current_sum = float(np.dot(w, b))
    needed_sum = target * 100.0

    if abs(needed_sum - current_sum) < 1e-6:
        scores = [round(float(p), 1) for p in b]
        achieved = round(current_sum / 100.0, 1)
        return {
            "baseline_overall": round(baseline, 1),
            "target_overall": round(target, 1),
            "achieved_overall": achieved,
            "feasible": True,
            "statements": _inverse_statement_rows(
                cols=cols,
                labels=labels,
                sections=sections,
                section_names=section_names,
                base=base,
                weights=weights,
                scores=scores,
            ),
            "method": "simplex_lp",
            "solver": "revised simplex",
            "objective_label": "Minimize weighted change (high-importance first)",
            "formula": "OSAT = Σ(performance × reduced importance) / 100",
            "solver_message": "Target already met at current scores.",
        }

    # Variables: d_plus[i], d_minus[i]  →  p[i] = b[i] + d_plus[i] - d_minus[i]
    inv_w = 1.0 / np.maximum(w, 1e-9)
    c = np.concatenate([inv_w, inv_w])

    a_eq = np.zeros((1, 2 * n), dtype=float)
    a_eq[0, :n] = w
    a_eq[0, n:] = -w
    b_eq = np.array([needed_sum - current_sum], dtype=float)

    bounds: list[tuple[float, float]] = []
    for i in range(n):
        bounds.append((0.0, max(0.0, 100.0 - float(b[i]))))
    for i in range(n):
        bounds.append((0.0, float(b[i])))

    lp = linprog(
        c,
        A_eq=a_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="revised simplex",
    )
    if not lp.success:
        lp = linprog(c, A_eq=a_eq, b_eq=b_eq, bounds=bounds, method="highs")

    if not lp.success:
        min_osat = 0.0
        max_osat = 100.0
        raise ValueError(
            f"Could not reach {target:.1f}% with current bounds "
            f"(achievable range ≈ {min_osat:.1f}%–{max_osat:.1f}%). "
            f"{lp.message}"
        )

    d_plus = lp.x[:n]
    d_minus = lp.x[n:]
    raw_scores = b + d_plus - d_minus
    scores = [round(float(max(0.0, min(100.0, p))), 1) for p in raw_scores]
    achieved = round(sum(p * wt for p, wt in zip(scores, weights)) / 100.0, 1)

    return {
        "baseline_overall": round(baseline, 1),
        "target_overall": round(target, 1),
        "achieved_overall": achieved,
        "feasible": True,
        "statements": _inverse_statement_rows(
            cols=cols,
            labels=labels,
            sections=sections,
            section_names=section_names,
            base=base,
            weights=weights,
            scores=scores,
        ),
        "method": "simplex_lp",
        "solver": "revised simplex",
        "objective_label": "Minimize weighted change (high-importance first)",
        "formula": "OSAT = Σ(performance × reduced importance) / 100",
        "solver_message": lp.message,
    }


def _scenario_card_from_rows(
    *,
    mode_id: str,
    title: str,
    baseline: float,
    achieved: float,
    target: float | None,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    changed = [r for r in rows if r.get("changed")]
    total_lift = round(sum(abs(float(r.get("delta_pts", 0))) for r in changed), 1)
    return {
        "id": mode_id,
        "title": title,
        "baseline_overall": round(baseline, 1),
        "achieved_overall": round(achieved, 1),
        "target_overall": round(target, 1) if target is not None else None,
        "total_lift": total_lift,
        "processes_changed": len(changed),
        "statements": rows,
    }


def compare_scenarios(
    snapshot: dict[str, Any],
    target_overall: float,
    *,
    top_down_option_index: int = 0,
) -> dict[str, Any]:
    """
    Side-by-side comparison of top-down and optimal plans.

    Recommends the plan that reaches the target with the lowest total lift
    (absolute point changes across changed processes).
    """
    statements = list(snapshot.get("statements") or [])
    if not statements:
        raise ValueError("Simulation data has no statements. Re-run gap analysis.")

    if snapshot.get("baseline_overall") is not None:
        baseline = float(snapshot["baseline_overall"])
    else:
        baseline = weighted_osat(statements)

    target = max(0.0, min(100.0, float(target_overall)))

    td = solve_top_down(snapshot, target, option_index=top_down_option_index)
    td_option = td.get("option") or {}
    top_down = _scenario_card_from_rows(
        mode_id="top-down",
        title="Top-down",
        baseline=baseline,
        achieved=float(td_option.get("achieved_overall", target)),
        target=target,
        rows=list(td_option.get("statements") or []),
    )
    top_down["option_title"] = td_option.get("title")

    opt = solve_optimal(snapshot, target)
    optimal = _scenario_card_from_rows(
        mode_id="optimal",
        title="Optimal",
        baseline=baseline,
        achieved=float(opt.get("achieved_overall", target)),
        target=target,
        rows=list(opt.get("statements") or []),
    )

    scenarios = [top_down, optimal]

    hitting = [
        s for s in scenarios if abs(s["achieved_overall"] - target) <= 0.15
    ]
    if not hitting:
        hitting = [s for s in scenarios if s["achieved_overall"] >= target - 0.15]
    if hitting:
        best = min(hitting, key=lambda s: (s["total_lift"], s["processes_changed"]))
    else:
        best = max(scenarios, key=lambda s: s["achieved_overall"])

    for s in scenarios:
        s["is_best"] = s["id"] == best["id"]

    by_col: dict[str, dict[str, Any]] = {}
    for scenario in scenarios:
        for row in scenario["statements"]:
            col = row["column"]
            if col not in by_col:
                by_col[col] = {
                    "column": col,
                    "label": row["label"],
                    "section": row.get("section"),
                    "section_name": row.get("section_name"),
                    "baseline": row["performance"],
                    "top_down": None,
                    "optimal": None,
                    "any_changed": False,
                }
            if scenario["id"] == "top-down":
                by_col[col]["top_down"] = row["required_performance"]
            elif scenario["id"] == "optimal":
                by_col[col]["optimal"] = row["required_performance"]
            if row["changed"]:
                by_col[col]["any_changed"] = True

    process_rows = [r for r in by_col.values() if r["any_changed"]]
    process_rows.sort(
        key=lambda r: (
            -(
                abs((r["optimal"] or r["baseline"]) - r["baseline"])
                + abs((r["top_down"] or r["baseline"]) - r["baseline"])
            ),
            r["label"],
        )
    )

    rec_name = best["title"]
    insight = (
        f"To reach {round(target)}% with the least effort, use the {rec_name} plan - "
        f"{best['total_lift']:.0f} points across {best['processes_changed']} process"
        f"{'' if best['processes_changed'] == 1 else 'es'}."
    )
    if best["id"] == "optimal":
        changed_labels = [
            r["label"] for r in best["statements"] if r.get("changed")
        ][:3]
        focus = " and ".join(changed_labels) if changed_labels else "high-importance drivers"
        insight = (
            f"To reach {round(target)}% with the least effort, use the Optimal plan - "
            f"concentrate on {focus} "
            f"({best['total_lift']:.0f} points across {best['processes_changed']} processes) "
            f"instead of spreading changes more widely."
        )

    return {
        "baseline_overall": round(baseline, 1),
        "target_overall": round(target, 1),
        "scenarios": scenarios,
        "best_scenario_id": best["id"],
        "process_rows": process_rows,
        "recommendation": {
            "scenario_id": best["id"],
            "title": best["title"],
            "insight": insight,
        },
        "guides": [
            {
                "id": "top-down",
                "title": "Top-down",
                "blurb": "Explore the different ways to hit a chosen target.",
            },
            {
                "id": "optimal",
                "title": "Optimal",
                "blurb": "Get the single most efficient plan to reach the target.",
            },
        ],
        "formula": "OSAT = Σ(performance × reduced importance) / 100",
    }


def save_simulation_json(path: Path, snapshot: dict[str, Any]) -> None:
    path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")


def load_simulation_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
