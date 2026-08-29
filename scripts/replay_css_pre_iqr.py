"""Rebuild style.css as it was immediately before the IQR shaded-graph request."""
from __future__ import annotations

import re
import runpy
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS_DIR = ROOT / "static" / "css"
PATCH_DIR = Path(__file__).resolve().parent / "_transcript_patches"
BACKUP = CSS_DIR / "style.backup.css"
OUT = CSS_DIR / "style.css"

MARKER_SHELL = "/* ---------- Shared site shell"
MARKER_LANDING = "/* ---------- Landing page ---------- */"

SIMULATION_BLOCK = """
/* ---------- Simulation page ---------- */
.sim-mode-tabs {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.sim-mode-btn {
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
}

.sim-mode-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.sim-mode-hint {
  margin: 0 0 16px;
  color: var(--text-secondary);
  font-size: 13px;
}

.sim-prompt {
  color: var(--text-secondary);
  font-size: 14px;
}

.sim-statements-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.sim-statement-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px 20px;
  align-items: center;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border-color);
}

.sim-statement-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.sim-statement-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.sim-statement-meta {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

.sim-statement-slider-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 220px;
}

.sim-statement-slider {
  flex: 1;
  accent-color: var(--accent-blue);
}

.sim-statement-value {
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--text-secondary);
  min-width: 88px;
  text-align: right;
}

.sim-result-label {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--text-secondary);
}

.sim-result-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.sim-result-main {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex-wrap: wrap;
}

.sim-result-value {
  font-size: 42px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
}

.sim-result-baseline {
  font-size: 13px;
  color: var(--text-muted);
}

.sim-result-delta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(63, 185, 80, 0.15);
  border: 1px solid rgba(63, 185, 80, 0.35);
  color: var(--success-green);
  font-size: 14px;
  font-weight: 600;
}

.sim-result-delta.is-negative {
  background: rgba(248, 81, 73, 0.12);
  border-color: rgba(248, 81, 73, 0.35);
  color: var(--error-red);
}

.sim-status-bar .status-center {
  color: var(--text-secondary);
}
"""

FINAL_FIXES = """
body.app-body .status-bar,
body.landing-body .status-bar {
  left: 0;
}

.missing-rate-hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px 40px;
  text-align: center;
}

.missing-rate-hero-value {
  font-size: clamp(3rem, 8vw, 4.5rem);
  font-weight: 700;
  line-height: 1;
  color: var(--text-primary);
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
}

.missing-rate-hero-label {
  margin-top: 14px;
  font-size: 14px;
  color: var(--text-secondary);
}

.respondent-cv-chart .cv-point {
  fill: #ffffff;
  opacity: 0.92;
}

.respondent-cv-chart .cv-point:hover {
  opacity: 1;
  fill: #ffffff;
}
"""

POST_PATCHES = [
    (
        """.gap-model-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 52px;
  position: relative;
  z-index: 50;
}""",
        """.gap-model-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 52px;
  position: relative;
  z-index: 50;
}

.gap-model-bar.is-quality-open {
  z-index: 200;
}""",
    ),
    (
        """.gap-model-quality-panel {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  z-index: 30;
  width: min(560px, 94vw);
  padding: 14px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}""",
        """.gap-model-quality-panel {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  z-index: 300;
  width: min(560px, 94vw);
  padding: 14px 16px;
  background: rgba(22, 27, 34, 0.96);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45);
}""",
    ),
    (
        """#gap-results {
  display: flex;
  flex-direction: column;
  gap: 16px;
}""",
        """#gap-loading {
  position: relative;
  z-index: 40;
}

#gap-loading.is-quality-open {
  z-index: 200;
}

#gap-results {
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: relative;
  z-index: 1;
}""",
    ),
    (
        """.respondent-cv-chart .cv-point {
  fill: var(--accent-blue);
  opacity: 0.75;
}

.respondent-cv-chart .cv-point:hover {
  opacity: 1;
  fill: #79c0ff;
}""",
        """.respondent-cv-chart .cv-point {
  fill: #ffffff;
  opacity: 0.92;
}

.respondent-cv-chart .cv-point:hover {
  opacity: 1;
  fill: #ffffff;
}""",
    ),
    (
        """.respondent-missing-scroll {
  max-height: 280px;
}

.respondent-missing-table {
  font-size: 12px;
}

.respondent-missing-table th,
.respondent-missing-table td {
  font-variant-numeric: tabular-nums;
}

.respondent-cv-chart-wrap {""",
        """.missing-rate-hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px 40px;
  text-align: center;
}

.missing-rate-hero-value {
  font-size: clamp(3rem, 8vw, 4.5rem);
  font-weight: 700;
  line-height: 1;
  color: var(--text-primary);
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
}

.missing-rate-hero-label {
  margin-top: 14px;
  font-size: 14px;
  color: var(--text-secondary);
}

.respondent-cv-chart-wrap {""",
    ),
]


def _original_base() -> str:
    lines = BACKUP.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith(MARKER_SHELL):
            return "\n".join(lines[:i]).rstrip() + "\n"
    return "\n".join(lines[:1497]).rstrip() + "\n"


def _landing_v38_css() -> str:
    src = (PATCH_DIR / "_landing_v38.py").read_text(encoding="utf-8")
    m = re.search(r'new_css = r"""(.*?)"""', src, re.S)
    if not m:
        raise RuntimeError("Could not parse landing v38 CSS")
    return m.group(1).strip() + "\n"


def _run_patch(name: str) -> None:
    path = PATCH_DIR / name
    if not path.exists():
        raise FileNotFoundError(path)
    shutil.copy2(OUT, PATCH_DIR / "style.css")
    if name == "_btn_unify.py":
        css_path = PATCH_DIR / "style.css"
        text = css_path.read_text(encoding="utf-8")
        text = text.replace(
            "body.app-body .data-table tbody tr:hover {\n  background: var(--glass-bg-hover);\n}\n\nbody.app-body .sim-mode-btn.is-active",
            "body.app-body .data-table tbody tr:hover,\nbody.app-body .browse-btn:hover {\n  background: var(--glass-bg-hover);\n}\n\nbody.app-body .sim-mode-btn.is-active",
            1,
        )
        css_path.write_text(text, encoding="utf-8")
    runpy.run_path(str(path), run_name="__patch__")
    shutil.copy2(PATCH_DIR / "style.css", OUT)


def main() -> None:
    text = _original_base()
    text = text.rstrip() + "\n" + SIMULATION_BLOCK.strip() + "\n"
    text = text.rstrip() + "\n\n" + MARKER_LANDING + "\n"

    OUT.write_text(text, encoding="utf-8")

    for patch in ("_landing_v38.py", "_app_shell.py", "_glass.py", "_btn_unify.py"):
        _run_patch(patch)

    text = OUT.read_text(encoding="utf-8")

    # De-duplicate accidental double site-page selector from patch overlap
    text = text.replace(
        ".site-page,\n.site-page,\n.landing-page {",
        ".site-page,\n.landing-page {",
        1,
    )

    for old, new in POST_PATCHES:
        if old not in text:
            print(f"WARN: patch block not found ({old[:60]}...)")
            continue
        text = text.replace(old, new, 1)

    # Remove any IQR / duplicate chart blocks if present
    text = re.sub(
        r"\n/\* ---------- Respondent CV charts ---------- \*/.*",
        "",
        text,
        flags=re.S,
    )
    text = text.replace(".respondent-cv-chart .cv-curve-iqr-fill {\n  fill: rgba(88, 166, 255, 0.22);\n  stroke: none;\n}\n\n", "")
    text = text.replace(".respondent-cv-chart .cv-curve-line {\n  fill: none;\n  stroke: rgba(255, 255, 255, 0.55);\n  stroke-width: 1.5;\n}\n", "")

    if ".missing-rate-hero {" not in text:
        text = text.rstrip() + "\n" + FINAL_FIXES.strip() + "\n"
    else:
        # Ensure cv points + status bar even if hero already present
        if "body.app-body .status-bar" not in text:
            text = text.rstrip() + "\n" + FINAL_FIXES.strip() + "\n"
        elif ".respondent-cv-chart .cv-point" not in text:
            text = text.rstrip() + """

.respondent-cv-chart .cv-point {
  fill: #ffffff;
  opacity: 0.92;
}

.respondent-cv-chart .cv-point:hover {
  opacity: 1;
  fill: #ffffff;
}
"""

    # Panel width/z-index as of v43
    text = text.replace(
        """.gap-model-quality-panel {
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
}""",
        """.gap-model-quality-panel {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  z-index: 300;
  width: min(560px, 94vw);
  padding: 14px 16px;
  background: rgba(22, 27, 34, 0.96);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45);
}""",
        1,
    )

    OUT.write_text(text.rstrip() + "\n", encoding="utf-8")

    checks = [
        "body.app-body",
        ".landing-bg-curve",
        ".landing-nav-links a.is-active",
        "--glass-bg",
        "--btn-bg",
        ".sim-mode-tabs",
        ".missing-rate-hero",
        "#gap-loading.is-quality-open",
        "cv-curve-iqr-fill",
        MARKER_SHELL,
    ]
    print(f"Wrote {OUT} ({text.count(chr(10)) + 1} lines)")
    for c in checks:
        found = c in text
        label = "OK" if (found and c != "cv-curve-iqr-fill") or (not found and c == "cv-curve-iqr-fill") else "BAD"
        print(f"  {label}: {c}")


if __name__ == "__main__":
    main()
