from pathlib import Path

p = Path(__file__).parent / "style.css"
t = p.read_text(encoding="utf-8")

t = t.replace(
    ".landing-cta {\n  display: inline-flex;",
    ".landing-cta {\n  position: relative;\n  display: inline-flex;",
    1,
)

t = t.replace(
    ".landing-cta:hover {",
    """.landing-cta::before {
  content: "";
  position: absolute;
  left: 50%;
  bottom: -28px;
  width: 220px;
  height: 80px;
  transform: translateX(-50%);
  background: radial-gradient(ellipse at center, rgba(56, 139, 253, 0.45) 0%, transparent 72%);
  pointer-events: none;
  z-index: -1;
}

.landing-cta:hover {""",
    1,
)

p.write_text(t, encoding="utf-8")
print("ok")
