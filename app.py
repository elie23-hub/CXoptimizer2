"""
Satisfaction Gap Analyzer — Flask application entry point.
"""

from __future__ import annotations

import os
import pickle
import uuid
from io import BytesIO
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, session, send_file, url_for

from utils.gap_analysis import run_gap_analysis
from utils.gap_export import build_gap_analysis_xlsx
from utils.sim_export import build_bottom_up_xlsx, build_summary_xlsx, build_top_down_xlsx
from utils.data_loader import parse_survey_file
from utils.simulation import (
    build_biplot_points,
    build_simulation_snapshot,
    compare_scenarios,
    load_simulation_json,
    predict_bottom_up,
    save_simulation_json,
    solve_optimal,
    solve_top_down,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-in-production")
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB


def _resolve_upload_dir() -> Path:
    """
    Local dev uses ./uploads. Vercel serverless only allows writes under /tmp.
    Override with UPLOAD_DIR if needed.
    """
    if os.environ.get("UPLOAD_DIR"):
        base = Path(os.environ["UPLOAD_DIR"])
    elif os.environ.get("VERCEL"):
        base = Path("/tmp/gap-analyzer-uploads")
    else:
        base = Path(__file__).parent / "uploads"
    base.mkdir(parents=True, exist_ok=True)
    return base


UPLOAD_DIR = _resolve_upload_dir()

ALLOWED_EXTENSIONS = {".sav", ".xlsx", ".xls", ".csv"}


def _snapshot_from_payload(payload: dict | None) -> dict | None:
    if not payload:
        return None
    snap = payload.get("snapshot")
    return snap if isinstance(snap, dict) else None


def _load_snapshot(session_id: str, payload: dict | None = None) -> dict | None:
    """Load simulation snapshot from disk, or from client payload (serverless fallback)."""
    snap = load_simulation_json(_simulation_path(session_id))
    if snap:
        return snap
    snap = _snapshot_from_payload(payload)
    if snap:
        try:
            save_simulation_json(_simulation_path(session_id), snap)
        except OSError:
            pass
        return snap
    return None


def _simulation_meta_payload(
    snapshot: dict[str, Any], summary: dict | None = None
) -> dict[str, Any]:
    model = snapshot.get("model") or {}
    return {
        "ok": True,
        "filename": snapshot.get("filename")
        or (summary.get("filename") if summary else "")
        or session.get("filename", ""),
        "scale": snapshot.get("scale"),
        "metric": snapshot.get("metric"),
        "metric_label": snapshot.get("metric_label"),
        "baseline_overall": snapshot.get("baseline_overall"),
        "statements": snapshot.get("statements", []),
        "biplot": build_biplot_points(snapshot),
        "model": model,
        "respondents": model.get("n_respondents")
        or (summary.get("kept_rows") if summary else None),
        "kept_rows": summary.get("kept_rows") if summary else None,
        "raw_rows": summary.get("raw_rows") if summary else None,
        "api_version": "sim-v1",
    }


def _allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def _summary_path(session_id: str) -> Path:
    return UPLOAD_DIR / f"{session_id}_summary.pkl"


def _data_path(session_id: str) -> Path:
    return UPLOAD_DIR / f"{session_id}_data.pkl"


def _simulation_path(session_id: str) -> Path:
    return UPLOAD_DIR / f"{session_id}_simulation.json"


def _save_summary(session_id: str, summary: dict) -> None:
    with _summary_path(session_id).open("wb") as f:
        pickle.dump(summary, f)


def _load_summary(session_id: str) -> dict | None:
    path = _summary_path(session_id)
    if not path.exists():
        return None
    with path.open("rb") as f:
        return pickle.load(f)


def _clear_upload_files(session_id: str) -> None:
    for path in (
        _summary_path(session_id),
        _data_path(session_id),
        _simulation_path(session_id),
    ):
        if path.exists():
            path.unlink()


def _load_data(session_id: str):
    path = _data_path(session_id)
    if not path.exists():
        return None
    with path.open("rb") as f:
        return pickle.load(f)


def _has_upload_session() -> bool:
    session_id = session.get("session_id")
    if not session_id:
        return False
    return _data_path(session_id).exists() and _summary_path(session_id).exists()


def _require_upload():
    if not _has_upload_session():
        return None, (jsonify({"ok": False, "error": "No upload data. Please upload a file first."}), 400)
    return session["session_id"], None


def _session_id_or_error():
    """Session cookie id only (for serverless routes that accept client snapshot)."""
    session_id = session.get("session_id")
    if not session_id:
        return None, (
            jsonify({"ok": False, "error": "No upload session. Please upload a file first."}),
            400,
        )
    return session_id, None


def _validate_metric_scale(scale: str, metric: str) -> str | None:
    if scale not in ("1-5", "1-10"):
        return "Invalid scale. Choose 1–5 or 1–10."
    if scale == "1-5" and metric not in ("top2", "mean", "weighted"):
        return "For a 1–5 scale, choose top-2-box or mean."
    if scale == "1-10" and metric not in ("top3", "mean", "weighted"):
        return "For a 1–10 scale, choose top-3-box or mean."
    return None


def _section_names_from_summary(summary: dict) -> dict[str, str]:
    names: dict[str, str] = {}
    for sec in summary.get("sections", []):
        key = str(sec.get("section"))
        names[key] = str(sec.get("name", "")).strip()
    return names


def _format_singular_group(group: dict) -> str:
    variables = group.get("variables") or []
    if len(variables) == 2:
        return f"{variables[0]} ↔ {variables[1]}"
    if variables:
        return ", ".join(variables)
    return ""


def _singular_matrix_block_message(summary: dict) -> str | None:
    groups = summary.get("singular_groups") or []
    if not groups:
        return None
    pairs = [text for g in groups if (text := _format_singular_group(g))]
    detail = "; ".join(pairs) if pairs else "see Upload page"
    return (
        "Gap analysis is blocked: collinear statements form a singular matrix for MLR, "
        "so importance z-scores cannot be calculated reliably. "
        "Remove or combine one statement from each pair on the Upload page, then re-upload. "
        f"Detected: {detail}."
    )

def _save_parse_result(result, session_id: str) -> None:
    if result.df_processed is not None:
        with _data_path(session_id).open("wb") as f:
            pickle.dump(result.df_processed, f)


def _result_to_summary(result) -> dict:
    """Convert ParseResult to a dict stored on disk (not in the cookie)."""
    return {
        "success": result.success,
        "filename": result.filename,
        "file_size_kb": result.file_size_kb,
        "raw_rows": result.raw_rows,
        "kept_rows": result.kept_rows,
        "removed_blank_rows": result.removed_blank_rows,
        "total_statements": result.total_statements,
        "cant_say_cells": result.cant_say_cells,
        "code_6_count": result.code_6_count,
        "blank_count": result.blank_count,
        "imputed_cells": result.imputed_cells,
        "id_column": result.id_column,
        "osat_column": result.osat_column,
        "load_failed": result.load_failed,
        "columns_found": result.columns_found[:20],
        "sections": [
            {
                "section": s.section,
                "name": "",
                "count": s.count,
            }
            for s in result.sections
        ],
        "validation": result.validation,
        "detected_scale": result.detected_scale,
        "cant_say_code": result.cant_say_code,
        "singular_groups": result.singular_groups,
        "preview_rows": result.preview_rows,
        "preview_columns": result.preview_columns,
        "summary_stats": result.summary_stats,
        "respondent_missing": result.respondent_missing,
        "respondent_cv": result.respondent_cv,
        "question_labels": result.question_labels,
        "has_spss_labels": result.has_spss_labels,
        "error": result.error,
    }


def _process_upload(file_bytes: bytes, filename: str) -> tuple[dict, str | None]:
    """Parse file, persist to disk, return (summary, error_message)."""
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())

    session_id = session["session_id"]
    result = parse_survey_file(file_bytes, filename)
    summary = _result_to_summary(result)
    summary["data_revision"] = str(uuid.uuid4())

    _save_parse_result(result, session_id)
    _save_summary(session_id, summary)
    session["filename"] = result.filename
    session.modified = True

    error_message = result.error if result.error else None
    return summary, error_message


@app.route("/")
def index():
    return render_template("landing.html", active_page="home")


@app.route("/upload", methods=["GET", "POST"])
def upload_page():
    if request.method == "POST":
        uploaded = request.files.get("survey_file")

        if not uploaded or not uploaded.filename:
            session["flash_error"] = "Please choose a file to upload."
            return redirect(url_for("upload_page"))

        if not _allowed_file(uploaded.filename):
            session["flash_error"] = "Unsupported file type. Use .sav, .xlsx, .xls, or .csv."
            return redirect(url_for("upload_page"))

        file_bytes = uploaded.read()
        summary, error = _process_upload(file_bytes, uploaded.filename)
        if error:
            session["flash_error"] = error

        return redirect(url_for("upload_page"))

    # Fresh upload page — do not show previous session data (still saved on disk for analysis)
    return render_template(
        "upload.html",
        active_page="upload",
    )


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """AJAX upload — returns HTML fragment for immediate display."""
    uploaded = request.files.get("survey_file")

    if not uploaded or not uploaded.filename:
        return jsonify({"ok": False, "error": "Please choose a file to upload."}), 400

    if not _allowed_file(uploaded.filename):
        return jsonify({"ok": False, "error": "Unsupported file type. Use .sav, .xlsx, .xls, or .csv."}), 400

    try:
        file_bytes = uploaded.read()
        summary, error_message = _process_upload(file_bytes, uploaded.filename)
        html = render_template(
            "partials/upload_results.html",
            parse_result=summary,
            error_message=error_message,
            filename=uploaded.filename,
        )
        if not html.strip():
            return jsonify(
                {
                    "ok": False,
                    "error": error_message or "No results to display. Check your column names.",
                }
            ), 400

        return jsonify(
            {
                "ok": True,
                "success": summary.get("success", False),
                "filename": uploaded.filename,
                "session_id": session.get("session_id"),
                "data_revision": summary.get("data_revision"),
                "error": error_message,
                "html": html,
            }
        )
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Server error: {exc}"}), 500


@app.route("/api/section-names", methods=["GET"])
def get_section_names():
    """Return saved section labels for the current upload session."""
    if "session_id" not in session:
        return jsonify({"ok": True, "names": {}})

    summary = _load_summary(session["session_id"])
    if not summary:
        return jsonify({"ok": True, "names": {}})

    return jsonify({"ok": True, "names": _section_names_from_summary(summary)})


@app.route("/api/section-names", methods=["POST"])
def save_section_names():
    """Persist user-defined section labels from the questionnaire."""
    if "session_id" not in session:
        return jsonify({"ok": False, "error": "No upload session."}), 400

    summary = _load_summary(session["session_id"])
    if not summary:
        return jsonify({"ok": False, "error": "No upload data found."}), 400

    payload = request.get_json(silent=True) or {}
    names = payload.get("names", {})
    if not isinstance(names, dict):
        return jsonify({"ok": False, "error": "Invalid section names."}), 400

    for sec in summary.get("sections", []):
        key = str(sec.get("section"))
        if key in names:
            sec["name"] = str(names[key]).strip()

    _save_summary(session["session_id"], summary)
    return jsonify({"ok": True})


@app.route("/api/session/reset", methods=["POST"])
def reset_session():
    """Clear server upload data when the user reloads the page."""
    session_id = session.get("session_id")
    if session_id:
        _clear_upload_files(session_id)
    session.pop("session_id", None)
    session.pop("filename", None)
    session.pop("flash_error", None)
    session.modified = True
    return jsonify({"ok": True})


@app.route("/upload/clear", methods=["POST"])
def clear_upload():
    session_id = session.get("session_id")
    if session_id:
        _clear_upload_files(session_id)
    session.pop("session_id", None)
    session.pop("filename", None)
    session.pop("flash_error", None)
    session.modified = True
    return redirect(url_for("upload_page"))


@app.route("/gap-analysis")
def gap_analysis_page():
    return render_template(
        "gap_analysis.html",
        active_page="gap",
        filename=session.get("filename", ""),
    )


@app.route("/api/gap-analysis/meta")
def gap_analysis_meta():
    session_id, err = _require_upload()
    if err:
        return err

    summary = _load_summary(session_id)
    if not summary:
        return jsonify({"ok": False, "error": "Upload summary not found."}), 404

    sections = []
    for sec in summary.get("sections", []):
        name = str(sec.get("name", "")).strip()
        sections.append(
            {
                "id": str(sec.get("section")),
                "name": name or f"Section {sec.get('section')}",
                "count": sec.get("count", 0),
            }
        )

    return jsonify(
        {
            "ok": True,
            "session_id": session_id,
            "data_revision": summary.get("data_revision", ""),
            "filename": summary.get("filename") or session.get("filename", ""),
            "sections": sections,
            "total_statements": summary.get("total_statements", 0),
            "kept_rows": summary.get("kept_rows", 0),
            "metrics_by_scale": {
                "1-5": [
                    {"id": "top2", "label": "Top-2-box"},
                    {"id": "mean", "label": "mean"},
                ],
                "1-10": [
                    {"id": "top3", "label": "Top-3-box"},
                    {"id": "mean", "label": "mean"},
                ],
            },
            "scales": [
                {"id": "1-5", "label": "Scale 1–5"},
                {"id": "1-10", "label": "Scale 1–10"},
            ],
            "detected_scale": summary.get("detected_scale", "1-5"),
            "cant_say_code": summary.get("cant_say_code", 6),
            "singular_groups": summary.get("singular_groups", []),
            "analysis_blocked": bool(summary.get("singular_groups")),
            "analysis_block_reason": _singular_matrix_block_message(summary) or "",
            "api_version": "gap-v2",
        }
    )


@app.route("/api/gap-analysis/compute", methods=["POST"])
def gap_analysis_compute():
    session_id, err = _require_upload()
    if err:
        return err

    summary = _load_summary(session_id)
    df = _load_data(session_id)
    if summary is None or df is None:
        return jsonify({"ok": False, "error": "Upload data not found."}), 404

    payload = request.get_json(silent=True) or {}
    scale = payload.get("scale", "") or summary.get("detected_scale", "")
    metric = payload.get("metric", "")
    if metric == "weighted":
        metric = "mean"

    if not scale or not metric:
        return jsonify(
            {"ok": False, "error": "Choose both scale and metric before running analysis."}
        ), 400

    validation_error = _validate_metric_scale(scale, metric)
    if validation_error:
        return jsonify({"ok": False, "error": validation_error}), 400

    singular_error = _singular_matrix_block_message(summary)
    if singular_error:
        return jsonify({"ok": False, "error": singular_error}), 400

    osat_column = summary.get("osat_column")
    try:
        result = run_gap_analysis(
            df=df,
            osat_column=osat_column,
            scale=scale,
            metric=metric,
            section_names=_section_names_from_summary(summary),
            question_labels=summary.get("question_labels", []),
        )
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Analysis failed: {exc}"}), 500

    result["api_version"] = "gap-v2"

    snapshot = build_simulation_snapshot(
        result,
        scale=scale,
        metric=metric,
        filename=summary.get("filename") or session.get("filename", ""),
    )
    save_simulation_json(_simulation_path(session_id), snapshot)
    result["simulation_ready"] = True
    result["simulation_snapshot"] = snapshot
    result["simulation_meta"] = _simulation_meta_payload(snapshot, summary)

    return jsonify({"ok": True, **result})


@app.route("/api/gap-analysis/export-xlsx", methods=["POST"])
def gap_analysis_export_xlsx():
    session_id, err = _require_upload()
    if err:
        return err

    summary = _load_summary(session_id)
    df = _load_data(session_id)
    if summary is None or df is None:
        return jsonify({"ok": False, "error": "Upload data not found."}), 404

    payload = request.get_json(silent=True) or {}
    scale = payload.get("scale", "") or summary.get("detected_scale", "")
    metric = payload.get("metric", "")
    if metric == "weighted":
        metric = "mean"

    if not scale or not metric:
        return jsonify(
            {"ok": False, "error": "Choose both scale and metric before exporting."}
        ), 400

    validation_error = _validate_metric_scale(scale, metric)
    if validation_error:
        return jsonify({"ok": False, "error": validation_error}), 400

    singular_error = _singular_matrix_block_message(summary)
    if singular_error:
        return jsonify({"ok": False, "error": singular_error}), 400

    try:
        result = run_gap_analysis(
            df=df,
            osat_column=summary.get("osat_column"),
            scale=scale,
            metric=metric,
            section_names=_section_names_from_summary(summary),
            question_labels=summary.get("question_labels", []),
        )
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Export failed: {exc}"}), 500

    filename = summary.get("filename") or session.get("filename", "") or "gap_analysis"
    stem = Path(filename).stem or "gap_analysis"
    download_name = f"{stem}_gap_analysis.xlsx"

    try:
        xlsx_bytes = build_gap_analysis_xlsx(result, filename=filename)
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Could not build Excel file: {exc}"}), 500

    return send_file(
        BytesIO(xlsx_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=download_name,
    )


@app.route("/api/simulation/export-xlsx", methods=["POST"])
def simulation_export_xlsx():
    payload = request.get_json(silent=True) or {}
    session_id, snapshot, err = _simulation_session_and_snapshot(payload)
    if err:
        return err

    summary = _load_summary(session_id) if session_id else None
    mode = str(payload.get("mode") or "bottom-up").strip().lower()

    try:
        if mode == "top-down":
            try:
                target = float(payload.get("target_overall"))
            except (TypeError, ValueError):
                return jsonify(
                    {"ok": False, "error": "Enter a target overall satisfaction (0–100%)."}
                ), 400
            try:
                option_index = int(payload.get("option_index", 0))
            except (TypeError, ValueError):
                option_index = 0
            raw_quadrants = payload.get("quadrants")
            quadrants: list[str] | None = None
            if isinstance(raw_quadrants, list):
                quadrants = [str(q) for q in raw_quadrants]
            elif isinstance(raw_quadrants, str) and raw_quadrants.strip():
                quadrants = [q.strip() for q in raw_quadrants.split(",") if q.strip()]
            result = solve_top_down(
                snapshot,
                target,
                option_index=option_index,
                quadrants=quadrants,
            )
            xlsx_bytes = build_top_down_xlsx(snapshot, result, filename=_export_filename(summary))
            suffix = "simulation_top_down"
        else:
            scores = payload.get("scores") or {}
            if not isinstance(scores, dict):
                return jsonify({"ok": False, "error": "Invalid scores payload."}), 400
            result = predict_bottom_up(snapshot, scores)
            xlsx_bytes = build_bottom_up_xlsx(snapshot, result, filename=_export_filename(summary))
            suffix = "simulation_bottom_up"
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Export failed: {exc}"}), 500

    stem = Path(_export_filename(summary)).stem or "simulation"
    download_name = f"{stem}_{suffix}.xlsx"
    return send_file(
        BytesIO(xlsx_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=download_name,
    )


@app.route("/api/summary/export-xlsx", methods=["POST"])
def summary_export_xlsx():
    session_id, err = _require_upload()
    if err:
        return err

    snapshot = load_simulation_json(_simulation_path(session_id))
    if not snapshot:
        return jsonify(
            {
                "ok": False,
                "error": "Run gap analysis first to generate simulation data.",
                "needs_gap_analysis": True,
            }
        ), 400

    summary = _load_summary(session_id)
    payload = request.get_json(silent=True) or {}
    if not payload.get("top_down_result"):
        return jsonify(
            {
                "ok": False,
                "error": "No top-down simulation saved. Run simulation first.",
            }
        ), 400

    try:
        xlsx_bytes = build_summary_xlsx(
            snapshot,
            payload,
            filename=_export_filename(summary),
        )
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Export failed: {exc}"}), 500

    stem = Path(_export_filename(summary)).stem or "summary"
    download_name = f"{stem}_summary.xlsx"
    return send_file(
        BytesIO(xlsx_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=download_name,
    )


def _export_filename(summary: dict | None) -> str:
    if summary and summary.get("filename"):
        return str(summary["filename"])
    return session.get("filename", "") or "export"


@app.route("/simulation")
def simulation_page():
    return render_template(
        "simulation.html",
        active_page="simulation",
        filename=session.get("filename", ""),
    )


def _simulation_session_and_snapshot(
    payload: dict | None,
) -> tuple[str | None, dict | None, tuple | None]:
    """Resolve session id + simulation snapshot (disk or client payload)."""
    payload = payload or {}
    session_id, err = _session_id_or_error()
    if err and not _snapshot_from_payload(payload):
        return None, None, err
    if not session_id:
        session["session_id"] = str(uuid.uuid4())
        session.modified = True
        session_id = session["session_id"]

    snapshot = _load_snapshot(session_id, payload)
    if not snapshot:
        return session_id, None, (
            jsonify(
                {
                    "ok": False,
                    "error": "Run gap analysis first to generate simulation data.",
                    "needs_gap_analysis": True,
                }
            ),
            400,
        )
    return session_id, snapshot, None


@app.route("/api/simulation/meta", methods=["GET", "POST"])
def simulation_meta():
    payload = request.get_json(silent=True) if request.method == "POST" else {}
    _sid, snapshot, err = _simulation_session_and_snapshot(payload)
    if err:
        return err

    summary = _load_summary(_sid) if _sid else None
    return jsonify(_simulation_meta_payload(snapshot, summary))


@app.route("/api/simulation/predict", methods=["POST"])
def simulation_predict():
    payload = request.get_json(silent=True) or {}
    _sid, snapshot, err = _simulation_session_and_snapshot(payload)
    if err:
        return err

    scores = payload.get("scores") or {}
    if not isinstance(scores, dict):
        return jsonify({"ok": False, "error": "Invalid scores payload."}), 400

    try:
        result = predict_bottom_up(snapshot, scores)
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Simulation failed: {exc}"}), 500

    return jsonify({"ok": True, **result, "api_version": "sim-v1"})


@app.route("/api/simulation/top-down", methods=["POST"])
def simulation_top_down():
    payload = request.get_json(silent=True) or {}
    _sid, snapshot, err = _simulation_session_and_snapshot(payload)
    if err:
        return err

    try:
        target = float(payload.get("target_overall"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Enter a target overall satisfaction (0–100%)."}), 400

    try:
        option_index = int(payload.get("option_index", 0))
    except (TypeError, ValueError):
        option_index = 0

    raw_quadrants = payload.get("quadrants")
    quadrants: list[str] | None = None
    if isinstance(raw_quadrants, list):
        quadrants = [str(q) for q in raw_quadrants]
    elif isinstance(raw_quadrants, str) and raw_quadrants.strip():
        quadrants = [q.strip() for q in raw_quadrants.split(",") if q.strip()]

    try:
        result = solve_top_down(
            snapshot,
            target,
            option_index=option_index,
            quadrants=quadrants,
        )
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Top-down simulation failed: {exc}"}), 500

    return jsonify({"ok": True, **result, "api_version": "sim-v1"})


@app.route("/api/simulation/optimal", methods=["POST"])
def simulation_optimal():
    payload = request.get_json(silent=True) or {}
    _sid, snapshot, err = _simulation_session_and_snapshot(payload)
    if err:
        return err

    try:
        target = float(payload.get("target_overall"))
    except (TypeError, ValueError):
        return jsonify(
            {"ok": False, "error": "Enter a target overall satisfaction (0–100%)."}
        ), 400

    try:
        result = solve_optimal(snapshot, target)
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Optimal simulation failed: {exc}"}), 500

    return jsonify({"ok": True, **result, "api_version": "sim-v1"})


@app.route("/api/simulation/summary", methods=["POST"])
def simulation_summary():
    payload = request.get_json(silent=True) or {}
    _sid, snapshot, err = _simulation_session_and_snapshot(payload)
    if err:
        return err
    try:
        if payload.get("target_overall") is not None:
            target = float(payload.get("target_overall"))
        else:
            baseline = float(snapshot.get("baseline_overall") or 0)
            target = min(100.0, max(0.0, round(baseline + 5)))
    except (TypeError, ValueError):
        return jsonify(
            {"ok": False, "error": "Enter a target overall satisfaction (0–100%)."}
        ), 400

    try:
        option_index = int(payload.get("top_down_option_index", 0))
    except (TypeError, ValueError):
        option_index = 0

    try:
        result = compare_scenarios(
            snapshot,
            target,
            top_down_option_index=option_index,
        )
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Summary comparison failed: {exc}"}), 500

    return jsonify({"ok": True, **result, "api_version": "sim-v1"})


@app.route("/summary")
def summary_page():
    return render_template(
        "summary.html",
        active_page="summary",
        filename=session.get("filename", ""),
    )


@app.route("/statistics")
def statistics_page():
    return redirect(url_for("summary_page"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
