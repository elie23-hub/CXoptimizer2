from pathlib import Path

p = Path(__file__).parent / "style.css"
text = p.read_text(encoding="utf-8")
start = text.find("/* ---------- Landing page ---------- */")
if start == -1:
    raise SystemExit("start not found")

new_css = open(Path(__file__).parent / "_landing_v35.css", encoding="utf-8").read()
p.write_text(text[:start] + new_css + "\n", encoding="utf-8")
print("ok")
