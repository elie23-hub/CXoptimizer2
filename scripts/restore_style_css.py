"""Deprecated — use scripts/build_style_css.py instead."""
from pathlib import Path
import subprocess
import sys

if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    subprocess.run([sys.executable, str(root / "build_style_css.py")], check=True)
