"""
Build static/css/style.css from replayed patches + supplements.

Always run this after CSS changes instead of hand-editing style.css directly.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS_DIR = ROOT / "static" / "css"
STYLE = CSS_DIR / "style.css"
CANONICAL = CSS_DIR / "style.canonical.css"
SUPPLEMENTS = CSS_DIR / "style.supplements.css"
MANIFEST = CSS_DIR / "REQUIRED_SELECTORS.txt"

REQUIRED = [
    ":root",
    "--btn-bg",
    "body.app-body",
    "body.landing-body",
    ".landing-bg-curve",
    ".landing-nav-links a.is-active",
    "--glass-bg",
    ".summary-stats-block",
    ".summary-stats-panel.is-open",
    ".respondent-cv-chart-wrap--fit",
    ".respondent-cv-chart .cv-curve",
    ".respondent-cv-chart .cv-point",
    ".missing-rate-hero",
    "#gap-loading.is-quality-open",
    ".sim-mode-tabs",
    ".browse-track",
    ".gap-priority-card",
    "#gap-biplot .biplot-label",
]


def _inject_btn_tokens(text: str) -> str:
    if "--btn-bg:" in text.split("/* ---------- Reset")[0]:
        return text
    needle = '  --font:           "Inter", "Segoe UI", system-ui, -apple-system, sans-serif;\n}'
    insert = '''  --font:           "Inter", "Segoe UI", system-ui, -apple-system, sans-serif;
  --btn-bg:           rgba(18, 20, 26, 0.9);
  --btn-bg-hover:     rgba(28, 30, 38, 0.95);
  --btn-bg-active:    rgba(36, 40, 50, 0.98);
  --btn-border:       rgba(255, 255, 255, 0.14);
  --btn-border-hover: rgba(255, 255, 255, 0.22);
  --btn-border-active:rgba(255, 255, 255, 0.28);
  --btn-text:         #e8eaed;
  --btn-radius:       8px;
}'''
    if needle not in text:
        raise RuntimeError("Could not inject --btn-* tokens into :root")
    return text.replace(needle, insert, 1)


def _merge_supplements(text: str) -> str:
    text = _inject_btn_tokens(text)
    if not SUPPLEMENTS.exists():
        raise FileNotFoundError(SUPPLEMENTS)
    sup = SUPPLEMENTS.read_text(encoding="utf-8")

    # Replace summary-stats-panel block if replay left the old minimal version
    old_panel = """.summary-stats-panel {
  margin-bottom: 16px;
}"""
    new_panel = """.summary-stats-panel {
  display: none;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 16px;
}

.summary-stats-panel.is-open {
  display: flex;
}"""
    if old_panel in text:
        text = text.replace(old_panel, new_panel, 1)

    # Insert cv-curve before cv-point if point exists but curve missing
    if ".respondent-cv-chart .cv-curve" not in text:
        anchor = ".respondent-cv-chart .cv-x-tick-label {"
        insert = """.respondent-cv-chart .cv-curve {
  fill: none;
  stroke: var(--accent-blue);
  stroke-width: 2;
}

"""
        if anchor in text:
            text = text.replace(anchor, insert + anchor, 1)

    # Append supplements (idempotent — skip rules already present)
    if ".summary-stats-block {" not in text:
        text = text.rstrip() + "\n\n" + sup.strip() + "\n"
    else:
        extras = []
        if ".respondent-cv-chart-wrap--fit" not in text:
            extras.append(_extract_rule(sup, ".respondent-cv-chart-wrap--fit"))
        if "#gap-biplot .biplot-label" not in text:
            extras.append(_extract_rule(sup, "#gap-biplot .biplot-leader"))
            extras.append(_extract_rule(sup, "#gap-biplot .biplot-label"))
        if ".summary-stats-block .table-wrapper" not in text:
            extras.append(_extract_rule(sup, ".summary-stats-block .table-wrapper"))
        if extras:
            text = text.rstrip() + "\n\n" + "\n\n".join(e for e in extras if e) + "\n"

    return text


def _extract_rule(css: str, selector: str) -> str:
    idx = css.find(selector)
    if idx == -1:
        return ""
    start = css.rfind("\n\n", 0, idx)
    start = 0 if start == -1 else start + 2
    nxt = css.find("\n\n", idx)
    return css[start:] if nxt == -1 else css[start:nxt]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    replay = ROOT / "scripts" / "replay_css_pre_iqr.py"
    subprocess.run([sys.executable, str(replay)], check=True, cwd=str(ROOT))

    text = STYLE.read_text(encoding="utf-8")
    text = _merge_supplements(text)
    STYLE.write_text(text, encoding="utf-8")
    CANONICAL.write_text(text, encoding="utf-8")

    MANIFEST.write_text("\n".join(REQUIRED) + "\n", encoding="utf-8")

    missing = [s for s in REQUIRED if s not in text]
    digest = _sha256(STYLE)
    lines = text.count("\n") + 1

    print(f"Built {STYLE} ({lines} lines)")
    print(f"Canonical copy: {CANONICAL}")
    print(f"SHA-256: {digest}")
    if missing:
        print("MISSING required selectors:")
        for m in missing:
            print(f"  - {m}")
        return 1
    print(f"All {len(REQUIRED)} required selectors present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
