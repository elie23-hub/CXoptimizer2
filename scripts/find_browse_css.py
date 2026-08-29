import json
from pathlib import Path

path = Path(
    r"C:\Users\user\.cursor\projects\c-Users-user-Desktop-Internship\agent-transcripts"
    r"\1b9fcf12-d9f9-4b3a-968b-a476bc8ce3d9\1b9fcf12-d9f9-4b3a-968b-a476bc8ce3d9.jsonl"
)
for line in path.read_text(encoding="utf-8").splitlines():
    if "browse-track" not in line:
        continue
    obj = json.loads(line)
    for part in obj.get("message", {}).get("content", []):
        if part.get("type") != "tool_use":
            continue
        inp = part.get("input", {})
        for key in ("new_string", "contents"):
            text = inp.get(key, "")
            if "browse-track" in text and ".browse-fill" in text:
                print("===", inp.get("path", key), "===")
                start = text.find(".browse-track")
                if start == -1:
                    start = text.find(".file-browse-row")
                print(text[max(0, start - 200) : start + 1200])
                print()
