"""Restore complete CSS from known-good blocks."""
from pathlib import Path

css_path = Path(__file__).parent.parent / "static" / "css" / "style.css"
text = css_path.read_text(encoding="utf-8")

# Layout fixes
text = text.replace(
    """body {
  font-family: var(--font);
  background: var(--bg-body);
  color: var(--text-primary);
  display: flex;
  min-height: 100vh;
  font-size: 14px;
  line-height: 1.5;
}""",
    """body {
  font-family: var(--font);
  background: var(--bg-body);
  color: var(--text-primary);
  display: flex;
  min-height: 100vh;
  font-size: 14px;
  line-height: 1.5;
  overflow-x: hidden;
}""",
)

text = text.replace(
    """.main-wrapper {
  margin-left: var(--sidebar-width);
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}""",
    """.main-wrapper {
  margin-left: var(--sidebar-width);
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  min-width: 0;
  max-width: calc(100vw - var(--sidebar-width));
  overflow-x: hidden;
}""",
)

text = text.replace(
    """.main-content {
  flex: 1;
  padding: 24px 28px 80px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}""",
    """.main-content {
  flex: 1;
  padding: 24px 28px 80px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
  max-width: 100%;
}""",
)

BROWSE_OLD = """.file-browse-row {
  display: flex;
  align-items: stretch;
  width: 100%;
  max-width: 480px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  overflow: hidden;
  background: #e8eaed;
  position: relative;
}

.file-browse-row[data-uploading="true"] {
  border-color: var(--accent-blue-dim);
}

.dataset-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.file-browse-row {
  display: flex;
  align-items: stretch;
  width: 100%;
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  overflow: hidden;
  background: #e8eaed;
}

.browse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 18px;
  background: #fff;
  color: #1f2328;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border-right: 1px solid #d0d7de;
  white-space: nowrap;
  flex-shrink: 0;
  user-select: none;
}

.browse-btn:hover {
  background: #f6f8fa;
}

.file-name-display {
  flex: 1;
  display: flex;
  align-items: center;
  padding: 10px 14px;
  font-size: 13px;
  color: #57606a;
  background: #e8eaed;
  overflow: hidden;
  position: relative;
  min-height: 42px;
}

.browse-progress-fill {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 0%;
  background: var(--accent-blue-dim);
  opacity: 0.35;
  transition: width 0.2s ease;
  z-index: 0;
  pointer-events: none;
}

.file-name-text {
  position: relative;
  z-index: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-status-bar {
  width: 100%;
  max-width: 480px;
  padding: 12px 16px;
  border-radius: var(--radius);
  text-align: center;
  font-size: 14px;
  font-weight: 500;
  color: #fff;
  background: var(--accent-blue-dim);
}

.upload-status-bar[data-state="complete"] {
  background: var(--accent-blue-dim);
}

.upload-status-bar[data-state="error"] {
  background: #8b2e2e;
}
"""

BROWSE_NEW = Path(__file__).parent.joinpath("_browse_css_snippet.txt").read_text(encoding="utf-8")
# append state rules missing from short snippet
BROWSE_NEW += """

.file-browse-row:not(.is-uploading):not(.is-complete):not(.is-error) .browse-label {
  justify-content: flex-start;
}

.file-browse-row.is-uploading .browse-label {
  justify-content: center;
  color: #fff;
  text-shadow: 0 0 4px rgba(0, 0, 0, 0.3);
}

.file-browse-row.is-complete .browse-fill {
  width: 100% !important;
}

.file-browse-row.is-complete .browse-label {
  justify-content: center;
  color: #fff;
  font-size: 14px;
}

.file-browse-row.is-error .browse-fill {
  width: 100% !important;
  background: var(--error-red);
}

.file-browse-row.is-error .browse-label {
  justify-content: center;
  color: #fff;
}

.browse-label {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  padding: 0 14px;
  z-index: 1;
  font-size: 13px;
  font-weight: 500;
  color: #57606a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.browse-fill {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 0%;
  background: var(--accent-blue-dim);
  transition: width 0.3s ease;
  z-index: 0;
}
"""

# normalize snippet - use cleaner unified block
BROWSE_BLOCK = """
.file-browse-row {
  display: flex;
  align-items: stretch;
  width: 100%;
  max-width: 480px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  overflow: hidden;
  background: #e8eaed;
  position: relative;
}

.file-browse-row.is-uploading {
  border-color: var(--accent-blue-dim);
}

.file-browse-row.is-complete {
  border-color: var(--accent-blue-dim);
}

.file-browse-row.is-error {
  border-color: var(--error-red);
}

.browse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 18px;
  background: #fff;
  color: #1f2328;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border-right: 1px solid #d0d7de;
  white-space: nowrap;
  flex-shrink: 0;
  user-select: none;
  position: relative;
  z-index: 2;
}

.browse-btn:hover {
  background: #f6f8fa;
}

.browse-track {
  flex: 1;
  position: relative;
  min-height: 42px;
  min-width: 0;
  background: #e8eaed;
  overflow: hidden;
}

.browse-fill {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 0%;
  background: var(--accent-blue-dim);
  transition: width 0.3s ease;
  z-index: 0;
}

.browse-label {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  padding: 0 14px;
  z-index: 1;
  font-size: 13px;
  font-weight: 500;
  color: #57606a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-browse-row:not(.is-uploading):not(.is-complete):not(.is-error) .browse-label {
  justify-content: flex-start;
}

.file-browse-row.is-uploading .browse-label {
  justify-content: center;
  color: #fff;
  text-shadow: 0 0 4px rgba(0, 0, 0, 0.3);
}

.file-browse-row.is-complete .browse-fill {
  width: 100% !important;
}

.file-browse-row.is-complete .browse-label {
  justify-content: center;
  color: #fff;
  font-size: 14px;
}

.file-browse-row.is-error .browse-fill {
  width: 100% !important;
  background: var(--error-red);
}

.file-browse-row.is-error .browse-label {
  justify-content: center;
  color: #fff;
}
"""

if BROWSE_OLD in text:
    text = text.replace(BROWSE_OLD, BROWSE_BLOCK)
elif ".browse-track" not in text:
  # partial broken state: insert after dataset-label if exists
    marker = ".upload-form {\n  width: 100%;\n}"
    if marker in text:
        text = text.replace(marker, marker + "\n" + BROWSE_BLOCK)

EXTRA = """

/* ---------- MLR model status bar ---------- */
.gap-model-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 52px;
}

.gap-model-bar-left {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  min-width: 0;
  color: var(--text-secondary);
  font-size: 14px;
}

.gap-model-bar-copy {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.gap-model-note {
  font-size: 12px;
  line-height: 1.45;
  color: var(--text-muted);
}

.gap-model-bar-right {
  position: relative;
  flex-shrink: 0;
  margin-left: auto;
}

.gap-model-quality-btn {
  white-space: nowrap;
  border-color: var(--border-color);
  color: var(--text-primary);
  background: #21262d;
}

.gap-model-quality-btn:not(:disabled):hover {
  border-color: var(--accent-blue);
  color: var(--accent-blue);
}

.gap-model-quality-btn.is-open {
  border-color: var(--accent-blue);
  color: var(--accent-blue);
  background: rgba(88, 166, 255, 0.1);
}

.gap-model-quality-panel {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  z-index: 30;
  width: min(360px, 92vw);
  padding: 14px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}

.gap-model-quality-title {
  margin: 0 0 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.gap-model-quality-hint {
  margin: 0 0 10px;
  font-size: 12px;
  line-height: 1.45;
  color: var(--text-secondary);
}

.gap-model-quality-metrics {
  margin: 0;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 6px 12px;
  font-size: 12px;
}

.gap-model-quality-metrics dt {
  margin: 0;
  color: var(--text-muted);
}

.gap-model-quality-metrics dd {
  margin: 0;
  text-align: right;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.gap-model-quality-stale {
  margin: 0 0 10px;
  font-size: 12px;
  color: var(--warning-yellow);
}

.model-r2-good,
.model-rmse-good {
  color: var(--success-green);
  font-weight: 600;
}

.model-r2-weak,
.model-rmse-weak {
  color: var(--error-red);
  font-weight: 600;
}

/* ---------- Upload summary stats + respondent CV ---------- */
.data-preview-title-block {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.summary-stats-btn {
  font-size: 12px;
  padding: 4px 10px;
}

.summary-stats-btn.is-active {
  background: rgba(88, 166, 255, 0.15);
  border-color: var(--accent-blue);
  color: var(--accent-blue);
}

.summary-stats-panel {
  margin-bottom: 16px;
}

.summary-stats-scroll {
  max-height: 280px;
}

.summary-stats-table {
  font-size: 12px;
}

.summary-stats-table .summary-stat-col {
  position: sticky;
  left: 0;
  z-index: 2;
  background: var(--bg-card);
  min-width: 90px;
  font-weight: 600;
  text-align: left;
}

.summary-stats-table thead .summary-stat-col {
  z-index: 3;
}

.summary-responses-cell {
  font-variant-numeric: tabular-nums;
}

.respondent-cv-section {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.respondent-cv-title {
  margin: 0 0 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.respondent-cv-desc {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.45;
}

.respondent-cv-chart-wrap {
  width: 100%;
  max-width: 100%;
  height: 300px;
  overflow-x: auto;
  overflow-y: hidden;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  padding: 8px 8px 4px;
}

.respondent-cv-chart-inner {
  display: inline-block;
  height: 280px;
  vertical-align: top;
}

.respondent-cv-chart {
  display: block;
  height: 280px;
  max-width: none;
}

.respondent-cv-chart .cv-axis {
  stroke: var(--border-color);
  stroke-width: 1;
}

.respondent-cv-chart .cv-grid {
  stroke: rgba(48, 54, 61, 0.55);
  stroke-width: 1;
  stroke-dasharray: 3 4;
}

.respondent-cv-chart .cv-axis-label {
  fill: var(--text-secondary);
  font-size: 11px;
}

.respondent-cv-chart .cv-axis-tick {
  stroke: var(--border-color);
  stroke-width: 1;
}

.respondent-cv-chart .cv-x-tick-label {
  fill: var(--text-muted);
  font-size: 9px;
}

.respondent-cv-chart .cv-point {
  fill: var(--accent-blue);
  opacity: 0.75;
}

.respondent-cv-chart .cv-point:hover {
  opacity: 1;
  fill: #79c0ff;
}

.respondent-cv-footnote {
  margin-top: 10px;
}

/* ---------- Singular matrix / imputation alerts ---------- */
.impute-summary {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.impute-lead {
  margin: 0;
  color: var(--warning-yellow);
  font-size: 14px;
}

.impute-lead-spaced {
  margin-top: 10px;
}

.impute-note {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-secondary);
}

.singular-flag-list {
  margin: 8px 0 0;
  padding-left: 18px;
  color: var(--text-secondary);
  font-size: 13px;
}

.singular-group-item {
  margin-bottom: 4px;
}

.singular-pair-sep {
  margin: 0 6px;
  color: var(--warning-yellow);
}
"""

if ".gap-model-bar {" not in text:
    text = text.rstrip() + EXTRA

# backup
backup = css_path.with_suffix(".backup.css")
backup.write_text(text, encoding="utf-8")
css_path.write_text(text, encoding="utf-8")

checks = [
    ".browse-track",
    ".gap-stat-card",
    ".gap-model-bar",
    ".summary-stats-btn",
    ".respondent-cv-chart-wrap",
    ".data-preview-scroll",
]
print("Wrote", css_path, "lines", text.count("\n") + 1)
for c in checks:
    print(c, c in text)
