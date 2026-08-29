import json
from pathlib import Path

path = Path(
    r"C:\Users\user\.cursor\projects\c-Users-user-Desktop-Internship\agent-transcripts"
    r"\1b9fcf12-d9f9-4b3a-968b-a476bc8ce3d9\1b9fcf12-d9f9-4b3a-968b-a476bc8ce3d9.jsonl"
)
best = ""
for line in path.read_text(encoding="utf-8").splitlines():
    if "file-browse-row.is-uploading .browse-label" not in line:
        continue
    obj = json.loads(line)
    for part in obj.get("message", {}).get("content", []):
        if part.get("type") != "tool_use":
            continue
        text = part.get("input", {}).get("new_string", "")
        if "file-browse-row.is-uploading .browse-label" in text and len(text) > len(best):
            best = text
start = best.find(".browse-track {")
end = best.find(".file-browse-row.is-error .browse-fill", start)
end = best.find("}", end) + 1
end2 = best.find("\n", end)
if best[end:end+20].strip().startswith("background"):
    end = best.find("}", end) + 1
block = best[start:end]
print(block)
