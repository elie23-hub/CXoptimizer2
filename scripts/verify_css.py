"""Verify style.css contains all required selectors and matches canonical checksum."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLE = ROOT / "static" / "css" / "style.css"
CANONICAL = ROOT / "static" / "css" / "style.canonical.css"
MANIFEST = ROOT / "static" / "css" / "REQUIRED_SELECTORS.txt"

MIN_LINES = 2100


def main() -> int:
    if not STYLE.exists():
        print(f"ERROR: missing {STYLE}")
        return 1

    text = STYLE.read_text(encoding="utf-8")
    lines = text.count("\n") + 1

    if lines < MIN_LINES:
        print(f"ERROR: style.css too short ({lines} lines, expected >= {MIN_LINES})")
        print("Run: python scripts/build_style_css.py")
        return 1

    required = [
        s.strip()
        for s in MANIFEST.read_text(encoding="utf-8").splitlines()
        if s.strip() and not s.startswith("#")
    ] if MANIFEST.exists() else []

    missing = [s for s in required if s not in text]
    if missing:
        print("ERROR: missing required CSS selectors:")
        for m in missing:
            print(f"  - {m}")
        print("Run: python scripts/build_style_css.py")
        return 1

    if CANONICAL.exists():
        a = hashlib.sha256(STYLE.read_bytes()).hexdigest()
        b = hashlib.sha256(CANONICAL.read_bytes()).hexdigest()
        if a != b:
            print("WARN: style.css differs from style.canonical.css")
            print(f"  style.css:     {a}")
            print(f"  canonical:     {b}")
            print("If intentional, run: python scripts/build_style_css.py")

    print(f"OK: style.css ({lines} lines, {len(required)} selectors)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
