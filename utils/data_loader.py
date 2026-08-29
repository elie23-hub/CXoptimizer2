"""
Survey data loading, column detection (S#_Q# pattern), and preprocessing.
"""

from __future__ import annotations

import re
import tempfile
import os
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

from utils.summary_stats import (
    SummaryScale,
    compute_respondent_cv,
    compute_respondent_missing_table,
    compute_summary_stats,
)
from utils.vif_analysis import compute_singular_matrix_groups

ScaleKind = Literal["1-5", "1-10"]


@dataclass(frozen=True)
class ScaleRules:
    kind: ScaleKind

    @property
    def lo(self) -> int:
        return 1

    @property
    def hi(self) -> int:
        return 5 if self.kind == "1-5" else 10

    @property
    def cant_say_code(self) -> int:
        return 6 if self.kind == "1-5" else 11

    @classmethod
    def for_kind(cls, kind: str) -> "ScaleRules":
        return cls("1-10" if kind == "1-10" else "1-5")


DEFAULT_SCALE = ScaleRules("1-5")

# Matches column names like: S1_Q1, S1_Q1 Deliv., s2_q3 Staff
STATEMENT_PATTERN = re.compile(r"^S(\d+)_Q(\d+)", re.IGNORECASE)

# Questionnaire number at start of SPSS variable label (Q4.1, 4.2., etc.)
QUESTION_LABEL_PATTERNS = [
    re.compile(r"^(?P<qno>Q\s*\d+(?:\.\d+)+)\.?\s*(?P<text>.+)$", re.IGNORECASE),
    re.compile(r"^(?P<qno>\d+(?:\.\d+)+)\.?\s+(?P<text>.+)$", re.IGNORECASE),
]

PREVIEW_ROW_COUNT = 20

# Overall satisfaction column names (first match wins)
OSAT_PATTERNS = [
    re.compile(r"^OSAT$", re.IGNORECASE),
    re.compile(r"^Overall\s+OSAT$", re.IGNORECASE),
    re.compile(r"^OSAT_Overall$", re.IGNORECASE),
    re.compile(r"^OSAT\b", re.IGNORECASE),
    re.compile(r"overall", re.IGNORECASE),
]

# Respondent ID column names
ID_PATTERNS = [
    re.compile(r"^id\b", re.IGNORECASE),
    re.compile(r"respondent", re.IGNORECASE),
    re.compile(r"^R\d", re.IGNORECASE),
]

VALID_RATINGS = {1, 2, 3, 4, 5}


def detect_survey_scale(
    df: pd.DataFrame,
    statement_cols: list[str],
    osat_column: str | None = None,
) -> ScaleRules:
    """Infer 1–5 vs 1–10 from values present in statement / OSAT columns."""
    seen: set[int] = set()
    cols = list(statement_cols)
    if osat_column and osat_column in df.columns:
        cols.append(osat_column)

    for col in cols:
        if col not in df.columns:
            continue
        for val in df[col]:
            if _is_nan_like(val):
                continue
            try:
                n = int(round(float(val)))
            except (TypeError, ValueError):
                continue
            if n >= 1:
                seen.add(n)

    if seen & {7, 8, 9, 10, 11}:
        return ScaleRules("1-10")
    return ScaleRules("1-5")


def _scale_validation_items(
    df: pd.DataFrame, statement_cols: list[str], scale: ScaleRules
) -> tuple[list[dict[str, Any]], bool]:
    """Validation messages for detected scale and can't-say code rules."""
    items: list[dict[str, Any]] = []
    ok = True

    if not statement_cols:
        return items, ok

    arr = _values_to_rating_array(df, statement_cols)
    rounded = np.round(arr)
    valid = (
        _rating_valid_mask(arr, scale)
        | _cant_say_mask(arr, scale)
        | np.isnan(arr)
    )
    invalid_count = int((~valid & ~np.isnan(arr)).sum())

    if scale.kind == "1-10":
        items.append(
            {
                "ok": True,
                "text": (
                    "Detected 1–10 scale. Can't say = code 11 (imputed). "
                    "Code 6 is kept as a valid rating."
                ),
            }
        )
        n11 = int(_cant_say_mask(arr, scale).sum())
        if n11:
            items.append(
                {
                    "ok": True,
                    "text": f"Found {n11} can't say response{'s' if n11 != 1 else ''} (code 11).",
                }
            )
    else:
        n11 = int((rounded == 11).sum())
        if n11:
            ok = False
            items.append(
                {
                    "ok": False,
                    "text": (
                        f"Found {n11} code 11 value{'s' if n11 != 1 else ''} on a 1–5 scale. "
                        "Use code 6 for can't say, or upload as a 1–10 scale file."
                    ),
                }
            )
        else:
            items.append(
                {
                    "ok": True,
                    "text": "Detected 1–5 scale. Can't say = code 6 (imputed).",
                }
            )

    if invalid_count:
        ok = False
        wrong = scale.cant_say_code
        items.append(
            {
                "ok": False,
                "text": (
                    f"Found {invalid_count} invalid value{'s' if invalid_count != 1 else ''} "
                    f"outside {scale.lo}–{scale.hi} and not can't say (code {wrong})."
                ),
            }
        )

    return items, ok


# Legacy alias — prefer ScaleRules.cant_say_code


@dataclass
class ImputationRules:
    """
    SPSS (.sav): NaN = system missing (skip / not asked) — NOT treated as blank.
    Excel/CSV: empty cells become NaN — treated as blank.
    """
    treat_nan_as_blank: bool
    source_label: str = "file"


MIN_COL_RESPONSE_RATE = 0.05  # among section participants
MIN_COL_GLOBAL_RESPONSE_RATE = 0.80  # column shown to <80% of sample → NaN is routing


@dataclass
class BlankContext:
    """Context for detecting true blanks vs structural SPSS missing."""
    rules: ImputationRules
    section_by_col: dict[str, int]
    col_response_rates: dict[str, float]
    col_global_rates: dict[str, float]
    statement_cols: list[str]


def _is_nan_like(val) -> bool:
    if val is None:
        return True
    if isinstance(val, float) and np.isnan(val):
        return True
    if pd.isna(val):
        return True
    return False


def _has_response(val) -> bool:
    """True when the respondent gave a rating (1–5) or code 6."""
    return is_valid_rating(val) or is_cant_say(val)


def _respondent_participated_in_section(row: pd.Series, section: int, ctx: BlankContext) -> bool:
    """True if respondent answered (rating or code 6) another question in the same section."""
    for other_col in ctx.statement_cols:
        if ctx.section_by_col.get(other_col) == section and _has_response(row[other_col]):
            return True
    return False


def _respondent_answered_same_section(row: pd.Series, col: str, ctx: BlankContext) -> bool:
    """True if respondent participated in this column's section (excluding this cell)."""
    section = ctx.section_by_col.get(col)
    if section is None:
        return False
    for other_col in ctx.statement_cols:
        if other_col == col:
            continue
        if ctx.section_by_col.get(other_col) == section and _has_response(row[other_col]):
            return True
    return False


def _column_global_rates(df: pd.DataFrame, statement_cols: list[str]) -> dict[str, float]:
    """Share of respondents with any answer (1–5 or code 6) on each column."""
    n = len(df)
    rates: dict[str, float] = {}
    for col in statement_cols:
        if n == 0:
            rates[col] = 0.0
        else:
            answered = sum(1 for v in df[col] if _has_response(v))
            rates[col] = answered / n
    return rates


def _column_response_rates(df: pd.DataFrame, ctx: BlankContext) -> dict[str, float]:
    """
    Per-column fielding rate among respondents who participated in that section.
    Better than global rates for routed / screened SPSS surveys.
    """
    rates: dict[str, float] = {}
    for col in ctx.statement_cols:
        section = ctx.section_by_col.get(col)
        if section is None:
            rates[col] = 0.0
            continue
        eligible = 0
        answered = 0
        for _, row in df.iterrows():
            if _respondent_participated_in_section(row, section, ctx):
                eligible += 1
                if _has_response(row[col]):
                    answered += 1
        rates[col] = answered / eligible if eligible else 0.0
    return rates


def is_empty_cell(val) -> bool:
    """Empty / NaN cell on a statement (not a valid 1–5 rating, not code 6)."""
    if is_valid_rating(val) or is_cant_say(val):
        return False
    if isinstance(val, str) and val.strip() == "":
        return True
    return _is_nan_like(val)


def needs_imputation(val, row: pd.Series | None = None, col: str | None = None, ctx: BlankContext | None = None) -> bool:
    return is_cant_say(val) or is_empty_cell(val)


def is_blank_cell(val, row: pd.Series, col: str, ctx: BlankContext) -> bool:
    return is_empty_cell(val)


def cell_has_no_response(val) -> bool:
    """No rating 1–5 and not code 6 (used to drop empty respondent rows)."""
    return not is_valid_rating(val) and not is_cant_say(val)


def _values_to_rating_array(df: pd.DataFrame, statement_cols: list[str]) -> np.ndarray:
    """Numeric array for statement columns (NaN for empty / non-numeric)."""
    return df[statement_cols].to_numpy(dtype=float, copy=True)


def _rating_valid_mask(arr: np.ndarray, scale: ScaleRules = DEFAULT_SCALE) -> np.ndarray:
    return (arr >= scale.lo) & (arr <= scale.hi) & ~np.isnan(arr)


def _cant_say_mask(arr: np.ndarray, scale: ScaleRules = DEFAULT_SCALE) -> np.ndarray:
    return np.round(arr) == scale.cant_say_code


def _code6_mask(arr: np.ndarray, scale: ScaleRules = DEFAULT_SCALE) -> np.ndarray:
    """Backward-compatible alias for can't-say mask."""
    return _cant_say_mask(arr, scale)


def _empty_mask(arr: np.ndarray) -> np.ndarray:
    return np.isnan(arr)


def count_missing_cells(
    df: pd.DataFrame, statement_cols: list[str], scale: ScaleRules = DEFAULT_SCALE
) -> tuple[int, int, int]:
    """Count missing across all statements. Returns (total, can't say, empty)."""
    arr = _values_to_rating_array(df, statement_cols)
    cant_say = int(_cant_say_mask(arr, scale).sum())
    blanks = int(_empty_mask(arr).sum())
    return cant_say + blanks, cant_say, blanks


def triple_mean_impute_dataframe(
    df: pd.DataFrame,
    statement_cols: list[str],
    grand_mean: float | None,
    col_means: dict[str, float],
    scale: ScaleRules = DEFAULT_SCALE,
) -> tuple[pd.DataFrame, int, int, int]:
    """Vectorized triple-mean imputation. Returns (df, total, can't say, blank)."""
    if not statement_cols:
        return df, 0, 0, 0

    arr = _values_to_rating_array(df, statement_cols)
    valid = _rating_valid_mask(arr, scale)
    cant_say = _cant_say_mask(arr, scale)
    empty = _empty_mask(arr)
    impute = cant_say | empty

    if not impute.any():
        return df, 0, 0, 0

    row_sums = (arr * valid).sum(axis=1)
    row_counts = valid.sum(axis=1)
    person_means = np.where(row_counts > 0, row_sums / row_counts, np.nan)

    col_mean_arr = np.array([col_means.get(col, np.nan) for col in statement_cols])
    gm = grand_mean if grand_mean is not None else np.nan

    imputed_count = 0
    imputed_code6 = 0
    imputed_blank = 0

    for j in range(len(statement_cols)):
        need = impute[:, j]
        if not need.any():
            continue

        pm = person_means[need]
        n_need = int(need.sum())
        stack = np.column_stack(
            [
                pm,
                np.full(n_need, col_mean_arr[j]),
                np.full(n_need, gm),
            ]
        )
        arr[need, j] = np.round(np.nanmean(stack, axis=1), 2)

        imputed_count += n_need
        imputed_code6 += int(cant_say[need].sum())
        imputed_blank += int(empty[need].sum())

    df = df.copy()
    df[statement_cols] = arr
    return df, imputed_count, imputed_code6, imputed_blank


def is_cant_say(val, scale: ScaleRules = DEFAULT_SCALE) -> bool:
    """True only for the scale's can't-say code (6 on 1–5, 11 on 1–10)."""
    if val is None or (isinstance(val, float) and np.isnan(val)) or pd.isna(val):
        return False
    if isinstance(val, str) and val.strip() == "":
        return False
    try:
        return int(round(float(val))) == scale.cant_say_code
    except (TypeError, ValueError):
        return False


def is_valid_rating(val, scale: ScaleRules = DEFAULT_SCALE) -> bool:
    """True for in-scale ratings only (1–5 or 1–10)."""
    if val is None or (isinstance(val, float) and np.isnan(val)) or pd.isna(val):
        return False
    if isinstance(val, str) and val.strip() == "":
        return False
    try:
        n = int(round(float(val)))
        return scale.lo <= n <= scale.hi
    except (TypeError, ValueError):
        return False


def _rules_for_file(filename: str) -> ImputationRules:
    ext = Path(filename).suffix.lower()
    if ext == ".sav":
        return ImputationRules(
            treat_nan_as_blank=False,
            source_label="SPSS",
        )
    return ImputationRules(
        treat_nan_as_blank=True,
        source_label="Excel/CSV",
    )


@dataclass
class StatementColumn:
    column: str
    section: int
    question: int
    label: str  # short display label after S#_Q# code


@dataclass
class SectionInfo:
    section: int
    statements: list[StatementColumn] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.statements)


@dataclass
class ParseResult:
    success: bool
    filename: str
    file_size_kb: float
    raw_rows: int
    kept_rows: int
    removed_blank_rows: int
    total_statements: int
    cant_say_cells: int
    imputed_cells: int
    id_column: str | None
    osat_column: str | None
    sections: list[SectionInfo]
    statement_columns: list[StatementColumn]
    validation: list[dict[str, Any]]
    preview_rows: list[dict[str, Any]]
    preview_columns: list[dict[str, str]]
    summary_stats: dict[str, Any] = field(default_factory=dict)
    respondent_missing: dict[str, Any] = field(default_factory=dict)
    respondent_cv: dict[str, Any] = field(default_factory=dict)
    question_labels: list[dict[str, str]] = field(default_factory=list)
    has_spss_labels: bool = False
    error: str | None = None
    columns_found: list[str] = field(default_factory=list)
    load_failed: bool = False
    code_6_count: int = 0
    blank_count: int = 0
    dropped_empty_statements: list[str] = field(default_factory=list)
    detected_scale: str = "1-5"
    cant_say_code: int = 6
    singular_groups: list[dict[str, Any]] = field(default_factory=list)
    # Legacy fields — kept so older app instances don't crash on upload
    structural_missing_count: int = 0
    total_empty_cells: int = 0
    valid_rating_cells: int = 0
    df_processed: pd.DataFrame | None = None


def _short_label(column_name: str, section: int, question: int) -> str:
    """Extract display label from column name, e.g. 'S1_Q1 Deliv.' -> 'Deliv.'"""
    prefix = f"S{section}_Q{question}"
    remainder = column_name[len(prefix) :].strip(" _-.")
    if remainder:
        return remainder[:12] + ("…" if len(remainder) > 12 else "")
    return f"S{section}_Q{question}"


def _lookup_column_label(column_labels: dict[str, str], column: str) -> str:
    """Match SPSS label to dataframe column (exact or case-insensitive)."""
    if column in column_labels:
        return column_labels[column]
    col_lower = column.strip().lower()
    for key, label in column_labels.items():
        if key.strip().lower() == col_lower:
            return label
    return ""


def _extract_question_parts(
    raw_label: str, section: int, question: int, column: str
) -> tuple[str, str]:
    """Parse questionnaire number + text from an SPSS / column label."""
    raw = raw_label.strip()
    fallback_no = f"S{section}_Q{question}"

    if not raw:
        return fallback_no, column

    for pattern in QUESTION_LABEL_PATTERNS:
        match = pattern.match(raw)
        if match:
            qno = re.sub(r"\s+", "", match.group("qno")).rstrip(".")
            text = match.group("text").strip()
            return qno, text or raw

    return fallback_no, raw


def _build_question_label_item(
    column: str,
    section: int,
    question: int,
    column_labels: dict[str, str],
) -> dict[str, str]:
    """Build question number + label row for the labels panel."""
    raw = _lookup_column_label(column_labels, column).strip()
    question_no, label_text = _extract_question_parts(raw, section, question, column)

    return {
        "variable": column,
        "question_no": question_no,
        "label": label_text,
        "full_label": raw or column,
    }


def _detect_id_column(columns: list[str]) -> str | None:
    for col in columns:
        for pattern in ID_PATTERNS:
            if pattern.search(col):
                return col
    return columns[0] if columns else None


def _detect_osat_column(columns: list[str], statement_cols: list[str]) -> str | None:
    candidates = [c for c in columns if c not in statement_cols]
    for col in candidates:
        for pattern in OSAT_PATTERNS:
            if pattern.search(col):
                return col
    return None


def detect_empty_statement_columns(
    df: pd.DataFrame, statement_cols: list[str], scale: ScaleRules = DEFAULT_SCALE
) -> list[str]:
    """Statement columns with no in-scale rating and no can't-say code on any row."""
    if not statement_cols:
        return []
    arr = _values_to_rating_array(df, statement_cols)
    has_response = _rating_valid_mask(arr, scale) | _cant_say_mask(arr, scale)
    return [
        statement_cols[i]
        for i in range(len(statement_cols))
        if not bool(has_response[:, i].any())
    ]


def detect_statement_columns(columns: list[str]) -> list[StatementColumn]:
    statements: list[StatementColumn] = []
    for col in columns:
        match = STATEMENT_PATTERN.match(col.strip())
        if match:
            section = int(match.group(1))
            question = int(match.group(2))
            statements.append(
                StatementColumn(
                    column=col,
                    section=section,
                    question=question,
                    label=_short_label(col, section, question),
                )
            )
    statements.sort(key=lambda s: (s.section, s.question))
    return statements


def group_sections(statements: list[StatementColumn]) -> list[SectionInfo]:
    sections_map: dict[int, SectionInfo] = {}
    for stmt in statements:
        if stmt.section not in sections_map:
            sections_map[stmt.section] = SectionInfo(section=stmt.section)
        sections_map[stmt.section].statements.append(stmt)
    return [sections_map[k] for k in sorted(sections_map)]


def load_file(file_bytes: bytes, filename: str) -> tuple[pd.DataFrame, dict[str, str]]:
    """Load file and return dataframe plus column labels (SPSS variable labels when available)."""
    column_labels: dict[str, str] = {}
    if not file_bytes:
        raise ValueError("The uploaded file is empty. Please choose a different file.")

    ext = Path(filename).suffix.lower()

    if ext == ".sav":
        import pyreadstat

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".sav", delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            df, meta = pyreadstat.read_sav(
                tmp_path,
                user_missing=True,  # keep code 6 as 6, not NaN
                apply_value_formats=False,
            )
            df.columns = [str(c).strip() for c in df.columns]
            names = [str(c).strip() for c in meta.column_names]
            labels = meta.column_labels or [""] * len(names)
            for name, label in zip(names, labels):
                if label:
                    column_labels[name] = str(label).strip()
            # Align labels to dataframe columns by position when names differ slightly
            for i, col in enumerate(df.columns):
                if col in column_labels:
                    continue
                if i < len(labels) and labels[i]:
                    column_labels[col] = str(labels[i]).strip()
            return df, column_labels
        except Exception as exc:
            hint = (
                "Could not read this SPSS (.sav) file. "
                "Check that it opens correctly in SPSS, then try exporting again. "
                f"Technical detail: {exc}"
            )
            raise ValueError(hint) from exc
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    buffer = BytesIO(file_bytes)

    if ext in {".xlsx", ".xls"}:
        df = pd.read_excel(buffer)
        df.columns = [str(c).strip() for c in df.columns]
        return df, column_labels

    if ext == ".csv":
        df = pd.read_csv(buffer)
        df.columns = [str(c).strip() for c in df.columns]
        return df, column_labels

    raise ValueError(f"Unsupported file type: {ext}. Use .sav, .xlsx, .xls, or .csv")


def _valid_rating_values(series: pd.Series, scale: ScaleRules = DEFAULT_SCALE) -> list[float]:
    """Extract numeric in-scale ratings from a series."""
    out: list[float] = []
    for val in series:
        if is_valid_rating(val, scale):
            out.append(float(val))
    return out


def _compute_reference_means(
    df: pd.DataFrame, statement_cols: list[str], scale: ScaleRules = DEFAULT_SCALE
) -> tuple[float | None, dict[str, float]]:
    """
    Grand mean (all valid ratings, all statements) and per-statement means.
    Computed from original data before imputation.
    """
    all_ratings: list[float] = []
    col_means: dict[str, float] = {}

    for col in statement_cols:
        col_vals = _valid_rating_values(df[col], scale)
        if col_vals:
            col_means[col] = sum(col_vals) / len(col_vals)
            all_ratings.extend(col_vals)

    grand_mean = sum(all_ratings) / len(all_ratings) if all_ratings else None
    return grand_mean, col_means


def triple_mean_impute(
    row: pd.Series,
    ctx: BlankContext,
    grand_mean: float | None,
    col_means: dict[str, float],
) -> tuple[pd.Series, int, int, int]:
    """
    Impute code 6 / true blanks with:
      average(respondent mean, statement mean, sample mean)
    """
    imputed_count = 0
    imputed_code6 = 0
    imputed_blank = 0
    values = row[ctx.statement_cols].copy()

    for col in ctx.statement_cols:
        val = values[col]
        if not needs_imputation(val, row, col, ctx):
            continue

        was_code6 = is_cant_say(val)
        was_blank = is_empty_cell(val)

        person_ratings: list[float] = []
        for other_col in ctx.statement_cols:
            if other_col == col:
                continue
            other_val = values[other_col]
            if is_valid_rating(other_val):
                person_ratings.append(float(other_val))

        components: list[float] = []
        if person_ratings:
            components.append(sum(person_ratings) / len(person_ratings))
        if col in col_means:
            components.append(col_means[col])
        if grand_mean is not None:
            components.append(grand_mean)

        if not components:
            continue

        values[col] = round(sum(components) / len(components), 2)
        imputed_count += 1
        if was_code6:
            imputed_code6 += 1
        if was_blank:
            imputed_blank += 1

    return values, imputed_count, imputed_code6, imputed_blank


def parse_survey_file(file_bytes: bytes, filename: str) -> ParseResult:
    """Full pipeline: load, detect structure, clean, validate, preview."""
    file_size_kb = round(len(file_bytes) / 1024, 1)

    try:
        df, column_labels = load_file(file_bytes, filename)
    except Exception as exc:
        return ParseResult(
            success=False,
            filename=filename,
            file_size_kb=file_size_kb,
            raw_rows=0,
            kept_rows=0,
            removed_blank_rows=0,
            total_statements=0,
            cant_say_cells=0,
            imputed_cells=0,
            id_column=None,
            osat_column=None,
            sections=[],
            statement_columns=[],
            validation=[],
            preview_rows=[],
            preview_columns=[],
            error=str(exc),
            columns_found=[],
            load_failed=True,
        )

    raw_rows = len(df)
    columns = [str(c) for c in df.columns]
    statements = detect_statement_columns(columns)

    if not statements:
        sample_cols = ", ".join(columns[:8])
        if len(columns) > 8:
            sample_cols += f", … ({len(columns)} columns total)"
        return ParseResult(
            success=False,
            filename=filename,
            file_size_kb=file_size_kb,
            raw_rows=raw_rows,
            kept_rows=0,
            removed_blank_rows=0,
            total_statements=0,
            cant_say_cells=0,
            imputed_cells=0,
            id_column=None,
            osat_column=None,
            sections=[],
            statement_columns=[],
            validation=[],
            preview_rows=[],
            preview_columns=[],
            columns_found=columns,
            error=(
                "No statement columns found. Column names must start with S1_Q1, S1_Q2, S2_Q1 … "
                f"(S = section, Q = question). Columns in your file: {sample_cols}"
            ),
        )

    statement_col_names = [s.column for s in statements]
    id_column = _detect_id_column(columns)
    osat_column = _detect_osat_column(columns, statement_col_names)
    scale = detect_survey_scale(df, statement_col_names, osat_column)

    dropped_empty = detect_empty_statement_columns(df, statement_col_names, scale)
    if dropped_empty:
        dropped_set = set(dropped_empty)
        statements = [s for s in statements if s.column not in dropped_set]
        statement_col_names = [s.column for s in statements]

    if not statements:
        return ParseResult(
            success=False,
            filename=filename,
            file_size_kb=file_size_kb,
            raw_rows=raw_rows,
            kept_rows=0,
            removed_blank_rows=0,
            total_statements=0,
            cant_say_cells=0,
            imputed_cells=0,
            id_column=None,
            osat_column=None,
            sections=[],
            statement_columns=[],
            validation=[],
            preview_rows=[],
            preview_columns=[],
            columns_found=columns,
            dropped_empty_statements=dropped_empty,
            error=(
                "All statement columns were empty (no responses on any row). "
                f"Dropped: {', '.join(dropped_empty)}"
            ),
        )

    sections = group_sections(statements)

    # Remove rows with no response on any statement (vectorized)
    stmt_arr = _values_to_rating_array(df, statement_col_names)
    has_response = _rating_valid_mask(stmt_arr, scale) | _cant_say_mask(stmt_arr, scale)
    blank_mask = ~has_response.any(axis=1)
    removed_blank_rows = int(blank_mask.sum())
    df = df.loc[~blank_mask].copy()

    cant_say_cells, code_6_count, blank_count = count_missing_cells(
        df, statement_col_names, scale
    )

    # Reference means from original valid ratings (before imputation)
    grand_mean, col_means = _compute_reference_means(df, statement_col_names, scale)
    df_before_impute = df.copy()

    # Triple-mean imputation (vectorized)
    df, total_imputed, verified_code6, verified_blank = triple_mean_impute_dataframe(
        df,
        statement_col_names,
        grand_mean,
        col_means,
        scale,
    )

    # Build validation checklist
    validation: list[dict[str, Any]] = []
    scale_ok = True
    if osat_column:
        validation.append({"ok": True, "text": "Overall satisfaction column found."})
    else:
        validation.append(
            {
                "ok": False,
                "text": "Overall satisfaction column not found (looked for OSAT / Overall).",
            }
        )

    scale_items, scale_ok = _scale_validation_items(df, statement_col_names, scale)
    validation.extend(scale_items)

    if dropped_empty:
        if len(dropped_empty) == 1:
            drop_text = (
                f"1 statement column dropped — no responses on any row: {dropped_empty[0]}."
            )
        else:
            drop_text = (
                f"{len(dropped_empty)} statement columns dropped — no responses on any row: "
                + ", ".join(dropped_empty)
                + "."
            )
        validation.append({"ok": True, "text": drop_text})
    else:
        validation.append(
            {"ok": True, "text": "No statement columns dropped (all had at least one response)."}
        )

    if removed_blank_rows > 0:
        validation.append(
            {
                "ok": True,
                "text": f"{removed_blank_rows} row{'s' if removed_blank_rows != 1 else ''} removed — blank on every statement.",
            }
        )
    else:
        validation.append({"ok": True, "text": "No fully blank rows removed."})

    cant_say_label = f"code {scale.cant_say_code}"
    if total_imputed > 0:
        validation.append(
            {
                "ok": True,
                "text": (
                    f"Triple-mean imputation applied to {total_imputed} of "
                    f"{cant_say_cells} missing cells "
                    f"({code_6_count} {cant_say_label}, {blank_count} empty)."
                ),
            }
        )
    else:
        validation.append(
            {
                "ok": True,
                "text": f"No {cant_say_label} or blank cells needed imputation.",
            }
        )

    all_valid = all(v["ok"] for v in validation) and osat_column is not None and scale_ok

    has_spss_labels = bool(column_labels) and Path(filename).suffix.lower() == ".sav"
    question_labels = [
        _build_question_label_item(stmt.column, stmt.section, stmt.question, column_labels)
        for stmt in statements
    ]

    label_map = {
        item.get("variable", ""): item.get("label", "")
        for item in question_labels
        if item.get("variable")
    }
    singular_result = compute_singular_matrix_groups(df, statement_col_names, label_map)
    singular_groups = singular_result.get("groups") or []

    # Preview columns — variable names as headers (SPSS-style grid)
    preview_columns: list[dict[str, str]] = []
    if id_column:
        preview_columns.append({"key": id_column, "label": id_column, "type": "id"})
    if osat_column:
        preview_columns.append({"key": osat_column, "label": osat_column, "type": "osat"})
    for stmt in statements:
        preview_columns.append(
            {"key": stmt.column, "label": stmt.column, "type": "rating"}
        )

    preview_rows: list[dict[str, Any]] = []
    preview_slice = df_before_impute.head(PREVIEW_ROW_COUNT)
    if extra_cols := [c for c in (id_column, osat_column) if c]:
        preview_cols = extra_cols + [c for c in statement_col_names if c not in extra_cols]
        preview_slice = df_before_impute[preview_cols].head(PREVIEW_ROW_COUNT)

    for _, row in preview_slice.iterrows():
        preview_row: dict[str, Any] = {}
        for col_def in preview_columns:
            key = col_def["key"]
            val = row.get(key, "")
            if isinstance(val, pd.Series):
                val = val.iloc[0] if len(val) else ""
            if pd.isna(val):
                preview_row[key] = ""
            elif col_def["type"] == "rating":
                try:
                    preview_row[key] = int(float(val))
                except (ValueError, TypeError):
                    preview_row[key] = val
            else:
                preview_row[key] = val
        preview_rows.append(preview_row)

    summary_scale = SummaryScale(lo=scale.lo, hi=scale.hi, cant_say=scale.cant_say_code)
    summary_stats = compute_summary_stats(
        df_before_impute,
        preview_columns,
        scale=summary_scale,
    )
    respondent_missing = compute_respondent_missing_table(
        df_before_impute,
        statement_col_names,
        id_column=id_column,
        scale=summary_scale,
    )
    respondent_cv = compute_respondent_cv(
        df_before_impute,
        statement_col_names,
        id_column=id_column,
        scale=summary_scale,
    )

    return ParseResult(
        success=all_valid,
        filename=filename,
        file_size_kb=file_size_kb,
        raw_rows=raw_rows,
        kept_rows=len(df),
        removed_blank_rows=removed_blank_rows,
        total_statements=len(statements),
        cant_say_cells=cant_say_cells,
        code_6_count=code_6_count,
        blank_count=blank_count,
        imputed_cells=total_imputed,
        id_column=id_column,
        osat_column=osat_column,
        sections=sections,
        statement_columns=statements,
        validation=validation,
        preview_rows=preview_rows,
        preview_columns=preview_columns,
        summary_stats=summary_stats,
        respondent_missing=respondent_missing,
        respondent_cv=respondent_cv,
        question_labels=question_labels,
        has_spss_labels=has_spss_labels,
        columns_found=columns,
        dropped_empty_statements=dropped_empty,
        detected_scale=scale.kind,
        cant_say_code=scale.cant_say_code,
        singular_groups=singular_groups,
        error=None if all_valid else "Some validation checks failed. See the list below.",
        df_processed=df,
    )


def section_display_name(section_num: int) -> str:
    """Default section label — customize in template or config later."""
    names = {
        1: "Logistics",
        2: "Staff & service",
        3: "Booking & pricing",
    }
    return names.get(section_num, f"Section {section_num}")
