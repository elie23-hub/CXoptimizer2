import json
from pathlib import Path

path = Path(
    r"C:\Users\user\.cursor\projects\c-Users-user-Desktop-Internship\agent-transcripts"
    r"\1b9fcf12-d9f9-4b3a-968b-a476bc8ce3d9\1b9fcf12-d9f9-4b3a-968b-a476bc8ce3d9.jsonl"
)
best = ""
for line in path.read_text(encoding="utf-8").splitlines():
    if "browse-track" not in line or "is-uploading" not in line:
        continue
    obj = json.loads(line)
    for part in obj.get("message", {}).get("content", []):
        if part.get("type") != "tool_use":
            continue
        inp = part.get("input", {})
        text = inp.get("new_string", "")
        if ".browse-track" in text and ".file-browse-row.is-error" in text and len(text) > len(best):
            best = text
# extract from browse-btn or file-browse-row to results-container
start = best.find(".file-browse-row {")
if start == -1:
    start = best.find(".browse-btn {")
end = best.find("/* ---------- Results area", start)
if end == -1:
    end = best.find(".results-container", start)
block = best[start:end].strip()
Path(__file__).parent / "_browse_css_snippet.txt"
Path(__file__).parent.joinpath("_browse_css_snippet.txt").write_text(block, encoding="utf-8")
print(len(block))
print(block)
