from pathlib import Path

p = Path(__file__).parent / "style.css"
text = p.read_text(encoding="utf-8")

old = """body.app-body .main-wrapper {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 1120px;
  margin: 0 auto;
  min-height: calc(100vh - 80px);
}

body.app-body .top-header {
  background: transparent;
  border-bottom: none;
  padding: 4px 0 18px;
}

body.app-body .main-content {
  padding-top: 0;
}"""

new = """body.app-body .main-wrapper {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 1400px;
  margin: 0 auto;
  min-height: calc(100vh - 80px);
}

body.app-body .top-header {
  background: transparent;
  border-bottom: none;
  padding: 4px 0 18px;
}

body.app-body .main-content {
  padding-top: 0;
  padding-left: 20px;
  padding-right: 20px;
}

/* Glass surfaces on app pages */
body.app-body {
  --glass-bg: rgba(22, 27, 34, 0.55);
  --glass-bg-hover: rgba(32, 38, 48, 0.65);
  --glass-border: rgba(255, 255, 255, 0.1);
  --glass-blur: 14px;
}

body.app-body .card,
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

body.app-body .data-table tbody tr:hover {
  background: var(--glass-bg-hover);
}

body.app-body .sim-mode-btn.is-active {
  background: rgba(31, 111, 235, 0.75);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
}"""

if old not in text:
    raise SystemExit("main block not found")
text = text.replace(old, new, 1)

text = text.replace(
    "  max-width: 1120px;\n  padding: 22px 0 0;",
    "  max-width: 1400px;\n  padding: 22px 0 0;",
    1,
)

p.write_text(text, encoding="utf-8")
print("ok")
