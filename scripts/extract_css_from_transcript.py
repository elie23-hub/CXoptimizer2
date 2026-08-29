"""Extract style.css-related tool payloads from agent transcript."""
import json
import re
from pathlib import Path

TRANSCRIPT = Path(
    r"C:\Users\user\.cursor\projects\c-Users-user-Desktop-Internship\agent-transcripts"
    r"\1b9fcf12-d9f9-4b3a-968b-a476bc8ce3d9\1b9fcf12-d9f9-4b3a-968b-a476bc8ce3d9.jsonl"
)
OUT = Path(__file__).parent / "_extracted_transcript_css.txt"

# Stop before IQR shading user message (line ~1299)
STOP_MARKERS = ("cv-curve-iqr-fill", "IQR shading", "area below the graph")

hits = []
line_no = 0
for raw in TRANSCRIPT.read_text(encoding="utf-8").splitlines():
    line_no += 1
    if any(m in raw for m in STOP_MARKERS):
        break
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        continue
    msg = obj.get("message", {})
    for part in msg.get("content", []):
        if part.get("type") != "tool_use":
            continue
        name = part.get("name", "")
        inp = part.get("input", {})
        path = inp.get("path", "")
        if "style.css" in str(path) or (
            name == "Write" and inp.get("path", "").endswith("style.css")
        ):
            hits.append((line_no, name, path, inp))
        if name == "Shell":
            cmd = inp.get("command", "")
            if "style.css" in cmd and ("write_text" in cmd or "contents" in cmd or "append" in cmd):
                hits.append((line_no, name, "shell", {"command": cmd[:12000]}))
        if name == "Write" and str(inp.get("path", "")).endswith((".py",)):
            contents = inp.get("contents", "")
            if "style.css" in contents and len(contents) > 500:
                hits.append((line_no, name, inp.get("path"), {"contents": contents[:15000]}))

with OUT.open("w", encoding="utf-8") as f:
    for line_no, name, path, inp in hits:
        f.write(f"\n{'='*80}\nLINE {line_no} | {name} | {path}\n{'='*80}\n")
        if "contents" in inp:
            f.write(inp["contents"])
            f.write("\n")
        elif "command" in inp:
            f.write(inp["command"])
            f.write("\n")
        elif "new_string" in inp:
            f.write("--- new_string ---\n")
            f.write(inp.get("new_string", "")[:8000])
            f.write("\n")

print(f"Wrote {len(hits)} hits to {OUT}")
