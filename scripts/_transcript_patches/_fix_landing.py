from pathlib import Path

p = Path(__file__).parent / "style.css"
text = p.read_text(encoding="utf-8")

replacements = [
(
"""/* ---------- Landing page ---------- */
body.landing-body {
  display: block;
  height: 100vh;
  max-height: 100vh;
  background: #04060f;
  overflow: hidden;
}

.landing-page {
  position: relative;
  height: 100vh;
  max-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 24px;
  overflow: hidden;
}""",
"""/* ---------- Landing page ---------- */
html:has(body.landing-body) {
  height: 100%;
}

body.landing-body {
  display: block;
  width: 100%;
  min-height: 100vh;
  height: 100vh;
  max-height: 100vh;
  margin: 0;
  background: #04060f;
  overflow: hidden;
}

.landing-page {
  position: relative;
  width: 100%;
  height: 100vh;
  max-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  padding: 0 24px;
  overflow: hidden;
}

.landing-horizon {
  position: absolute;
  top: 10%;
  left: 50%;
  width: 200%;
  height: 52%;
  transform: translateX(-50%);
  border-radius: 50%;
  pointer-events: none;
  background: radial-gradient(
    ellipse 46% 38% at 50% 0%,
    rgba(200, 225, 255, 0.65) 0%,
    rgba(120, 175, 255, 0.32) 20%,
    rgba(56, 139, 253, 0.14) 42%,
    rgba(31, 111, 235, 0.04) 58%,
    transparent 74%
  );
  filter: blur(10px);
  z-index: 0;
}

.landing-horizon-arc {
  position: absolute;
  top: 11.5%;
  left: 50%;
  width: min(920px, 115vw);
  height: 220px;
  transform: translateX(-50%);
  border-radius: 50%;
  border-top: 2px solid rgba(210, 235, 255, 0.95);
  box-shadow:
    0 0 18px rgba(160, 210, 255, 0.95),
    0 0 48px rgba(88, 166, 255, 0.55),
    0 0 100px rgba(56, 139, 253, 0.28);
  pointer-events: none;
  z-index: 1;
  opacity: 0.92;
}"""
),
(
""".landing-hero {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  width: 100%;
  max-width: 720px;
  margin: 0 auto;
  padding: 10vh 12px 24px;
  flex-shrink: 0;
}""",
""".landing-hero {
  position: relative;
  z-index: 2;
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  width: 100%;
  max-width: 720px;
  margin: 0 auto;
  padding: 0 12px 20px;
}"""
),
(
""".landing-preview {
  position: relative;
  z-index: 1;
  width: min(1040px, 94vw);
  max-height: min(42vh, 380px);
  margin-top: auto;
  flex-shrink: 0;
  overflow: hidden;
  perspective: 1200px;
}""",
""".landing-preview {
  position: relative;
  z-index: 1;
  width: min(1040px, 94vw);
  max-height: min(38vh, 340px);
  margin: 0 auto;
  flex-shrink: 0;
  overflow: hidden;
  perspective: 1200px;
  align-self: center;
}"""
),
(
"""@media (max-width: 640px) {
  .landing-hero {
    padding: 7vh 12px 16px;
  }""",
"""@media (max-width: 640px) {
  .landing-horizon-arc {
    width: 130vw;
    top: 9%;
    height: 160px;
  }

  .landing-hero {
    padding: 0 12px 12px;
  }"""
),
]

for old, new in replacements:
    if old not in text:
        raise SystemExit(f"block not found:\n{old[:80]}...")
    text = text.replace(old, new, 1)

p.write_text(text, encoding="utf-8")
print("patched")
