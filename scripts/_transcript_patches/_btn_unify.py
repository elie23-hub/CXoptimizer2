from pathlib import Path

p = Path(__file__).parent / "style.css"
text = p.read_text(encoding="utf-8")

# 1. Add button tokens to :root
text = text.replace(
    "  --font:           \"Segoe UI\", system-ui, -apple-system, sans-serif;\n}",
    """  --font:           "Segoe UI", system-ui, -apple-system, sans-serif;
  --btn-bg:           rgba(18, 20, 26, 0.9);
  --btn-bg-hover:     rgba(28, 30, 38, 0.95);
  --btn-bg-active:    rgba(36, 40, 50, 0.98);
  --btn-border:       rgba(255, 255, 255, 0.14);
  --btn-border-hover: rgba(255, 255, 255, 0.22);
  --btn-border-active:rgba(255, 255, 255, 0.28);
  --btn-text:         #e8eaed;
  --btn-radius:       8px;
}""",
    1,
)

# 2. Fix glass block - remove buttons
old_glass = """body.app-body .card,
body.app-body .gap-stat-card,
body.app-body .file-badge,
body.app-body .error-card,
body.app-body .gap-select,
body.app-body .sim-mode-btn,
body.app-body .gap-model-quality-panel,
body.app-body #gap-biplot,
body.app-body .data-table thead,
body.app-body .browse-track,
body.app-body .summary-stats-btn,
body.app-body .impute-option,
body.app-body .gap-priority-table thead {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border-color: var(--glass-border);
}

body.app-body .data-table tbody tr:hover,
body.app-body .browse-btn:hover {
  background: var(--glass-bg-hover);
}

body.app-body .sim-mode-btn.is-active {
  background: rgba(31, 111, 235, 0.75);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
}"""

new_glass = """body.app-body .card,
body.app-body .gap-stat-card,
body.app-body .file-badge,
body.app-body .error-card,
body.app-body .gap-select,
body.app-body .gap-model-quality-panel,
body.app-body #gap-biplot,
body.app-body .data-table thead,
body.app-body .browse-track,
body.app-body .impute-option,
body.app-body .gap-priority-table thead {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border-color: var(--glass-border);
}

body.app-body .data-table tbody tr:hover {
  background: var(--glass-bg-hover);
}"""

if old_glass not in text:
    raise SystemExit("glass block not found")
text = text.replace(old_glass, new_glass, 1)

# 3. Unified .btn styles
old_btn = """.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: var(--radius);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  text-decoration: none;
  transition: background 0.15s, opacity 0.15s;
}

.btn-primary {
  background: var(--accent-blue-dim);
  color: #fff;
}

.btn-primary:hover { background: var(--accent-blue); }

.btn-primary.disabled {
  opacity: 0.4;
  pointer-events: none;
}

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
}

.btn-ghost:hover {
  background: var(--bg-card-hover);
  color: var(--text-primary);
}

.btn-large {
  padding: 12px 28px;
  font-size: 14px;
}"""

new_btn = """.btn,
button.btn,
a.btn,
label.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 20px;
  border-radius: var(--btn-radius);
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  border: 1px solid var(--btn-border);
  background: var(--btn-bg);
  color: var(--btn-text);
  text-decoration: none;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease, opacity 0.15s ease;
}

.btn:hover:not(:disabled):not(.disabled),
button.btn:hover:not(:disabled),
a.btn:hover,
label.btn:hover {
  background: var(--btn-bg-hover);
  border-color: var(--btn-border-hover);
  color: var(--btn-text);
}

.btn:disabled,
.btn.disabled {
  opacity: 0.45;
  cursor: not-allowed;
  pointer-events: none;
}

.btn-primary,
.btn-ghost {
  background: var(--btn-bg);
  color: var(--btn-text);
  border: 1px solid var(--btn-border);
}

.btn-primary:hover:not(:disabled):not(.disabled),
.btn-ghost:hover:not(:disabled) {
  background: var(--btn-bg-hover);
  border-color: var(--btn-border-hover);
  color: var(--btn-text);
}

.btn-primary.disabled {
  opacity: 0.45;
  pointer-events: none;
}

.btn.is-active,
.btn-active {
  background: var(--btn-bg-active);
  border-color: var(--btn-border-active);
  color: var(--btn-text);
}

.btn-large {
  padding: 13px 28px;
  font-size: 14px;
}"""

if old_btn not in text:
    raise SystemExit("btn block not found")
text = text.replace(old_btn, new_btn, 1)

# 4. browse-btn
old_browse = """.browse-btn {
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
}"""

new_browse = """.browse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 18px;
  background: var(--btn-bg);
  color: var(--btn-text);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border-right: 1px solid var(--btn-border);
  white-space: nowrap;
  flex-shrink: 0;
  user-select: none;
  position: relative;
  z-index: 2;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.browse-btn:hover {
  background: var(--btn-bg-hover);
}"""

text = text.replace(old_browse, new_browse, 1)

# 5. export buttons
old_export = """.btn-export {
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
}"""

new_export = """.btn-export {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 22px;
  border-radius: var(--btn-radius);
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.01em;
  cursor: pointer;
  border: 1px solid var(--btn-border);
  background: var(--btn-bg);
  color: var(--btn-text);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.btn-export-primary,
.btn-export-outline {
  background: var(--btn-bg);
  color: var(--btn-text);
  border-color: var(--btn-border);
}

.btn-export-primary:hover:not(:disabled),
.btn-export-outline:hover:not(:disabled) {
  background: var(--btn-bg-hover);
  border-color: var(--btn-border-hover);
  color: var(--btn-text);
}"""

text = text.replace(old_export, new_export, 1)

# 6. sim-mode-btn
old_sim = """.sim-mode-btn {
  padding: 10px 22px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  background: #21262d;
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}

.sim-mode-btn:hover:not(:disabled) {
  border-color: var(--accent-blue);
  color: var(--text-primary);
}

.sim-mode-btn.is-active {
  background: var(--accent-blue-dim);
  border-color: var(--accent-blue);
  color: #fff;
}"""

new_sim = """.sim-mode-btn {
  padding: 10px 22px;
  border-radius: var(--btn-radius);
  border: 1px solid var(--btn-border);
  background: var(--btn-bg);
  color: var(--btn-text);
  font-size: 14px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.sim-mode-btn:hover:not(:disabled) {
  background: var(--btn-bg-hover);
  border-color: var(--btn-border-hover);
  color: var(--btn-text);
}

.sim-mode-btn.is-active {
  background: var(--btn-bg-active);
  border-color: var(--btn-border-active);
  color: var(--btn-text);
}"""

text = text.replace(old_sim, new_sim, 1)

# 7. gap-model-quality-btn
old_quality = """.gap-model-quality-btn {
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
}"""

new_quality = """.gap-model-quality-btn {
  white-space: nowrap;
}

.gap-model-quality-btn.is-open {
  background: var(--btn-bg-active);
  border-color: var(--btn-border-active);
  color: var(--btn-text);
}"""

text = text.replace(old_quality, new_quality, 1)

# 8. summary-stats-btn active
text = text.replace(
    """.summary-stats-btn.is-active {
  background: rgba(88, 166, 255, 0.15);
  border-color: var(--accent-blue);
  color: var(--accent-blue);
}""",
    """.summary-stats-btn.is-active {
  background: var(--btn-bg-active);
  border-color: var(--btn-border-active);
  color: var(--btn-text);
}""",
    1,
)

# 9. Align landing-btn with same tokens
text = text.replace(
    """.landing-btn--primary {
  background: rgba(18, 20, 26, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.14);
  color: #e8eaed;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
}

.landing-btn--primary:hover {
  background: rgba(28, 30, 38, 0.95);
  border-color: rgba(255, 255, 255, 0.22);
}""",
    """.landing-btn--primary {
  background: var(--btn-bg);
  border: 1px solid var(--btn-border);
  color: var(--btn-text);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
}

.landing-btn--primary:hover {
  background: var(--btn-bg-hover);
  border-color: var(--btn-border-hover);
}""",
    1,
)

p.write_text(text, encoding="utf-8")
print("ok")
