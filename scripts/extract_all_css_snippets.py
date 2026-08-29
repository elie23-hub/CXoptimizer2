"""Extract every style.css StrReplace/append from transcript (pre-IQR)."""
import json
import re
from pathlib import Path

TRANSCRIPT = Path(
    r"C:\Users\user\.cursor\projects\c-Users-user-Desktop-Internship\agent-transcripts"
    r"\1b9fcf12-d9f9-4b3a-968b-a476bc8ce3d9\1b9fcf12-d9f9-4b3a-968b-a476bc8ce3d9.jsonl"
)
OUT = Path(__file__).parent / "_css_snippets.txt"
STOP = "area below the graph"

snippets = []
for i, raw in enumerate(TRANSCRIPT.read_text(encoding="utf-8").splitlines(), 1):
    if STOP in raw:
        break
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        continue
    for part in obj.get("message", {}).get("content", []):
        if part.get("type") != "tool_use":
            continue
        name = part.get("name")
        inp = part.get("input")
        if not isinstance(inp, dict):
            continue
        path = inp.get("path", "")
        if path.endswith("style.css"):
            if inp.get("new_string") and len(inp["new_string"]) > 80:
                snippets.append((i, "strreplace", inp["new_string"]))
            if inp.get("contents") and len(inp["contents"]) > 5000:
                snippets.append((i, "write", inp["contents"][:500]))
        if name == "Shell":
            cmd = inp.get("command", "")
            if "style.css" in cmd and "summary-stats-block" in cmd:
                snippets.append((i, "shell", cmd[:4000]))

OUT.write_text(
    "\n\n".join(f"=== line {ln} ({kind}) ===\n{text}" for ln, kind, text in snippets),
    encoding="utf-8",
)
print(f"Wrote {len(snippets)} snippets to {OUT}")
for ln, kind, text in snippets:
    if "summary-stats-block" in text and kind != "write":
        print(f"  summary-stats @ line {ln}")
