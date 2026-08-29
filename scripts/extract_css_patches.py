import json
from pathlib import Path

path = Path(
    r"C:\Users\user\.cursor\projects\c-Users-user-Desktop-Internship\agent-transcripts"
    r"\1b9fcf12-d9f9-4b3a-968b-a476bc8ce3d9\1b9fcf12-d9f9-4b3a-968b-a476bc8ce3d9.jsonl"
)

needles = [
    "Question labels + data preview",
    "structure-name-input",
    "btn-export",
    "legend-overkill",
    "gap-export-row",
    "biplot-point",
    "gap-priority-card",
    "data-preview-card",
]

out = Path(__file__).parent / "_css_patches.txt"
chunks = []
for needle in needles:
    chunks.append(f"\n=== {needle} ===\n")
    for line in path.read_text(encoding="utf-8").splitlines():
        if needle not in line:
            continue
        obj = json.loads(line)
        for part in obj.get("message", {}).get("content", []):
            if part.get("type") != "tool_use":
                continue
            inp = part.get("input", {})
            if inp.get("path", "").endswith("style.css"):
                text = inp.get("new_string", "")
                if needle in text:
                    chunks.append(text)
                    chunks.append("\n")
                    break

out.write_text("".join(chunks), encoding="utf-8")
print("wrote", out)
