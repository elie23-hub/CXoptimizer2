"""Restore missing gap analysis and upload scroll CSS."""
from pathlib import Path

css_path = Path(__file__).parent.parent / "static" / "css" / "style.css"
text = css_path.read_text(encoding="utf-8")

# Fix table wrapper — scroll only inside dedicated containers
text = text.replace(
    """.table-wrapper {
  overflow-x: auto;
  border-radius: var(--radius);
  border: 1px solid var(--border-color);
}""",
    """.table-wrapper {
  border-radius: var(--radius);
  border: 1px solid var(--border-color);
  max-width: 100%;
}""",
)

# Results area clipping
text = text.replace(
    """.results-container {
  width: 100%;
}""",
    """.results-container {
  width: 100%;
  min-width: 0;
  max-width: 100%;
  overflow-x: hidden;
}""",
)

# Browse button (removed accidentally in a prior edit)
if ".browse-btn {" not in text:
    text = text.replace(
        ".file-browse-row.is-error {\n  border-color: var(--error-red);\n}",
        """.file-browse-row.is-error {
  border-color: var(--error-red);
}

.dataset-label {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
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
}""",
    )

# Structure list with editable names
text = text.replace(
    """/* ---------- Structure list ---------- */
.structure-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.structure-list li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #21262d;
  border-radius: 6px;
  border: 1px solid var(--border-color);
}

.structure-name { font-weight: 500; color: var(--text-primary); }
.structure-count { font-size: 12px; color: var(--text-secondary); }""",
    """/* ---------- Structure list ---------- */
.structure-hint {
  margin-bottom: 12px;
}

.structure-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.structure-list li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #21262d;
  border-radius: 6px;
  border: 1px solid var(--border-color);
}

.structure-code {
  font-size: 12px;
  font-weight: 600;
  color: var(--accent-blue);
  flex-shrink: 0;
}

.structure-name-input {
  flex: 1;
  min-width: 0;
  padding: 5px 8px;
  background: #161b22;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  color: var(--text-primary);
  font-size: 13px;
  font-family: inherit;
}

.structure-name-input::placeholder {
  color: var(--text-muted);
}

.structure-name-input:focus {
  outline: none;
  border-color: var(--accent-blue);
}

.structure-count {
  font-size: 12px;
  color: var(--text-secondary);
  flex-shrink: 0;
  white-space: nowrap;
}""",
)

MISSING = """

/* ---------- Question labels + data preview cards ---------- */
.question-labels-card,
.data-preview-card {
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
}

.question-labels-card .card-title-row,
.data-preview-card .card-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.question-label-search-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.question-label-search-wrap input {
  width: 160px;
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  font-size: 13px;
  font-family: inherit;
  background: #21262d;
  color: var(--text-primary);
}

.question-label-search-wrap input:focus {
  outline: none;
  border-color: var(--accent-blue);
}

.question-labels-scroll,
.data-preview-scroll {
  display: block;
  width: 100%;
  max-width: 100%;
  max-height: 360px;
  overflow: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
}

.preview-file-meta {
  font-size: 13px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.question-label-row.is-hidden { display: none; }

.var-cell {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
}

.question-label-cell {
  line-height: 1.45;
  min-width: 280px;
  max-width: 640px;
}

.question-labels-table,
.preview-grid-table {
  width: max-content;
  min-width: 100%;
}

.th-sort-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0;
  border: none;
  background: none;
  color: var(--text-primary);
  font: inherit;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
}

.th-sort-btn:hover { color: var(--accent-blue); }

.th-sort-btn[data-sort="asc"] .sort-arrows,
.th-sort-btn[data-sort="desc"] .sort-arrows {
  color: var(--accent-blue);
}

.sort-arrows {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1;
}

/* ---------- Gap analysis page ---------- */
.gap-toolbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.gap-toolbar-left {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.gap-select-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.gap-select-label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
}

.gap-select {
  min-width: 160px;
  padding: 8px 10px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: #21262d;
  color: var(--text-primary);
  font-size: 13px;
  font-family: inherit;
}

.gap-select:focus {
  outline: none;
  border-color: var(--accent-blue);
}

.gap-select:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.gap-prompt {
  color: var(--text-secondary);
  font-size: 14px;
}

.gap-loading {
  display: flex;
  align-items: center;
  gap: 16px;
  color: var(--text-secondary);
}

.loading-spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--border-color);
  border-top-color: var(--accent-blue);
  border-radius: 50%;
  animation: gap-spin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes gap-spin {
  to { transform: rotate(360deg); }
}

.gap-stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

@media (max-width: 800px) {
  .gap-stat-row { grid-template-columns: repeat(2, 1fr); }
}

.gap-stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.gap-stat-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
}

.gap-stat-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.gap-stat-urgent .gap-stat-value {
  color: var(--error-red);
}

.gap-chart-row {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 16px;
  align-items: start;
}

@media (max-width: 960px) {
  .gap-chart-row { grid-template-columns: 1fr; }
}

.gap-biplot-card,
.gap-priority-card {
  min-width: 0;
}

.biplot-wrap {
  width: 100%;
  overflow: hidden;
}

#gap-biplot {
  width: 100%;
  max-width: 100%;
  height: auto;
  display: block;
  background: #0d1117;
  border-radius: 6px;
  border: 1px solid var(--border-color);
}

#gap-biplot .biplot-point circle {
  transition: r 0.15s ease;
}

#gap-biplot .biplot-point text {
  pointer-events: none;
  user-select: none;
}

#gap-biplot .biplot-point:hover circle {
  r: 8;
}

.biplot-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 12px;
  font-size: 12px;
  color: var(--text-secondary);
}

.legend-item i {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}

.legend-maintain i { background: #38761d; }
.legend-low i { background: #bf9000; }
.legend-urgent i { background: #990000; }
.legend-overkill i { background: #1155cc; }

.gap-priority-card .card-title {
  margin-bottom: 8px;
}

.priority-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.priority-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  background: #21262d;
  border-radius: 6px;
  border: 1px solid var(--border-color);
}

.priority-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.priority-text strong {
  font-size: 13px;
  color: var(--text-primary);
}

.priority-sub {
  font-size: 11px;
  color: var(--text-muted);
}

.priority-gap {
  font-size: 12px;
  font-weight: 700;
  color: var(--error-red);
  flex-shrink: 0;
}

.priority-empty {
  font-size: 13px;
  color: var(--text-muted);
  padding: 8px 0;
}

.gap-table-card {
  min-width: 0;
  overflow: hidden;
}

.gap-table-scroll {
  max-width: 100%;
  overflow-x: auto;
  overflow-y: auto;
  max-height: 480px;
  overscroll-behavior: contain;
}

.gap-row-overall td {
  color: var(--error-red);
  font-weight: 600;
}

.gap-row-section td {
  background: #21262d;
  font-size: 12px;
  color: var(--accent-blue);
  padding-top: 12px;
}

.gap-negative {
  color: var(--error-red);
  font-weight: 600;
}

.z-cell {
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.position-cell {
  font-size: 12px;
  white-space: nowrap;
  padding: 5px 0;
  font-weight: 700;
  background: transparent;
  border: none;
}

.gap-export-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 12px;
  padding: 4px 0 12px;
}

.btn-export {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 22px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.01em;
  cursor: pointer;
  border: 1.5px solid transparent;
  transition: background 0.15s, border-color 0.15s, color 0.15s, box-shadow 0.15s, transform 0.1s;
}

.btn-export-primary {
  background: var(--accent-blue-dim);
  color: #fff;
  border-color: var(--accent-blue);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.25);
}

.btn-export-primary:hover:not(:disabled) {
  background: var(--accent-blue);
  border-color: var(--accent-blue);
  box-shadow: 0 4px 12px rgba(56, 139, 253, 0.35);
  transform: translateY(-1px);
}

.btn-export-outline {
  background: #fff;
  color: var(--accent-blue-dim);
  border-color: #fff;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.btn-export-outline:hover:not(:disabled) {
  background: #f0f6ff;
  border-color: var(--accent-blue);
  color: var(--accent-blue);
  box-shadow: 0 4px 12px rgba(56, 139, 253, 0.2);
  transform: translateY(-1px);
}

.btn-export:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.gap-status-bar .status-center {
  color: var(--text-secondary);
}

#gap-results {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
"""

if "/* ---------- Gap analysis page ---------- */" not in text:
    text = text.rstrip() + MISSING

css_path.write_text(text, encoding="utf-8")
print("Restored CSS:", css_path)
print("Has gap-stat-card:", ".gap-stat-card" in text)
print("Has data-preview-scroll:", ".data-preview-scroll" in text)
