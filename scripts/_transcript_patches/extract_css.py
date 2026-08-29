import json
import re
from pathlib import Path

path = Path(
    r"C:\Users\user\.cursor\projects\c-Users-user-Desktop-Internship\agent-transcripts"
    r"\1b9fcf12-d9f9-4b3a-968b-a476bc8ce3d9\1b9fcf12-d9f9-4b3a-968b-a476bc8ce3d9.jsonl"
)

best_gap = ""
best_full = ""
for line in path.read_text(encoding="utf-8").splitlines():
    if "style.css" not in line and "Gap analysis page" not in line:
        continue
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        continue
    for part in obj.get("message", {}).get("content", []):
        if part.get("type") != "tool_use":
            continue
        inp = part.get("input", {})
        for key in ("contents", "new_string", "command"):
            text = inp.get(key, "")
            if not text:
                continue
            if "Gap analysis page" in text:
                m = re.search(
                    r"/\* ---------- Gap analysis page ---------- \*/.*",
                    text,
                    re.S,
                )
                if m and len(m.group(0)) > len(best_gap):
                    best_gap = m.group(0).rstrip("'\"")
            if inp.get("path", "").endswith("style.css") and len(text) > len(best_full):
                if "Satisfaction Gap Analyzer" in text:
                    best_full = text

out = Path(__file__).parent.parent / "static" / "css"
(out / "_extracted_gap.css").write_text(best_gap, encoding="utf-8")
print("gap len", len(best_gap))
print("full len", len(best_full))
