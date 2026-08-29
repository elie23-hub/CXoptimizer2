"""Pull patch script contents from transcript jsonl."""
import json
from pathlib import Path

TRANSCRIPT = Path(
    r"C:\Users\user\.cursor\projects\c-Users-user-Desktop-Internship\agent-transcripts"
    r"\1b9fcf12-d9f9-4b3a-968b-a476bc8ce3d9\1b9fcf12-d9f9-4b3a-968b-a476bc8ce3d9.jsonl"
)
OUT_DIR = Path(__file__).parent / "_transcript_patches"
OUT_DIR.mkdir(exist_ok=True)

STOP = "area below the graph"

for i, raw in enumerate(TRANSCRIPT.read_text(encoding="utf-8").splitlines(), 1):
    if STOP in raw:
        print(f"Stopping at line {i}")
        break
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        continue
    for part in obj.get("message", {}).get("content", []):
        if part.get("type") != "tool_use" or part.get("name") != "Write":
            continue
        inp = part.get("input")
        if not isinstance(inp, dict):
            continue
        path = inp.get("path", "")
        contents = inp.get("contents", "")
        if not contents:
            continue
        if path.endswith("style.css") and len(contents) > 3000:
            out = OUT_DIR / f"line{i}_style.css"
            out.write_text(contents, encoding="utf-8")
            print(f"Saved full style.css from line {i}: {len(contents)} chars")
        elif "style.css" in contents and ("Path(__file__)" in contents or "style.css" in path):
            name = Path(path).name if path else f"patch_line{i}.py"
            out = OUT_DIR / name
            if not out.exists():
                out.write_text(contents, encoding="utf-8")
                print(f"Saved patch {name} from line {i}: {len(contents)} chars")
