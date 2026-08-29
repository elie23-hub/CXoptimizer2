from pathlib import Path

p = Path(__file__).parent / "style.css"
text = p.read_text(encoding="utf-8")
start = text.find("/* ---------- Landing page ---------- */")
if start == -1:
    raise SystemExit("start not found")

new_css = r"""/* ---------- Landing page ---------- */
body.landing-body {
  display: block;
  min-height: 100vh;
  background: #04060f;
  overflow-x: hidden;
}

.landing-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 28px 24px 0;
  overflow: hidden;
}

.landing-glow {
  position: absolute;
  pointer-events: none;
  border-radius: 50%;
}

.landing-glow--top {
  top: -42%;
  left: 50%;
  width: 140%;
  height: 70%;
  transform: translateX(-50%);
  background: radial-gradient(
    ellipse at center,
    rgba(56, 139, 253, 0.35) 0%,
    rgba(31, 111, 235, 0.12) 38%,
    transparent 72%
  );
}

.landing-glow--floor {
  bottom: 8%;
  left: 50%;
  width: 120%;
  height: 40%;
  transform: translateX(-50%);
  background: radial-gradient(
    ellipse at center,
    rgba(56, 139, 253, 0.18) 0%,
    transparent 70%
  );
}

.landing-stars {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    radial-gradient(1px 1px at 10% 20%, rgba(255, 255, 255, 0.35), transparent),
    radial-gradient(1px 1px at 30% 65%, rgba(255, 255, 255, 0.25), transparent),
    radial-gradient(1px 1px at 55% 15%, rgba(255, 255, 255, 0.3), transparent),
    radial-gradient(1px 1px at 72% 42%, rgba(255, 255, 255, 0.2), transparent),
    radial-gradient(1px 1px at 88% 78%, rgba(255, 255, 255, 0.28), transparent),
    radial-gradient(1px 1px at 18% 88%, rgba(255, 255, 255, 0.22), transparent);
}

.landing-header {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 1100px;
}

.landing-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--text-primary);
  font-weight: 600;
  font-size: 15px;
}

.landing-brand-icon {
  color: var(--accent-blue);
  font-size: 20px;
}

.landing-hero {
  position: relative;
  z-index: 2;
  text-align: center;
  max-width: 760px;
  margin-top: 72px;
  padding: 0 12px;
}

.landing-badge {
  display: inline-block;
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid rgba(56, 139, 253, 0.35);
  background: rgba(56, 139, 253, 0.08);
  color: #9ecbff;
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.02em;
  margin-bottom: 28px;
}

.landing-title {
  margin: 0 0 20px;
  font-size: clamp(2rem, 5vw, 3.25rem);
  font-weight: 700;
  line-height: 1.12;
  letter-spacing: -0.03em;
  color: #f0f6fc;
  text-shadow: 0 0 40px rgba(56, 139, 253, 0.25);
}

.landing-subtitle {
  margin: 0 auto 36px;
  max-width: 620px;
  font-size: clamp(0.95rem, 2vw, 1.05rem);
  line-height: 1.65;
  color: #9aa4b2;
}

.landing-cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 160px;
  padding: 14px 32px;
  border-radius: 999px;
  background: linear-gradient(180deg, #ffffff 0%, #e8eef7 100%);
  color: #0d1117;
  font-size: 15px;
  font-weight: 600;
  text-decoration: none;
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.08),
    0 8px 32px rgba(56, 139, 253, 0.35),
    0 2px 8px rgba(0, 0, 0, 0.4);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.landing-cta:hover {
  transform: translateY(-2px);
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.12),
    0 12px 40px rgba(56, 139, 253, 0.45),
    0 4px 12px rgba(0, 0, 0, 0.45);
}

.landing-preview {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 920px;
  margin-top: 56px;
  perspective: 1200px;
}

.landing-preview-window {
  border-radius: 14px 14px 0 0;
  border: 1px solid rgba(56, 139, 253, 0.25);
  border-bottom: none;
  background: rgba(13, 17, 23, 0.85);
  box-shadow:
    0 -8px 60px rgba(56, 139, 253, 0.2),
    0 24px 80px rgba(0, 0, 0, 0.55);
  transform: rotateX(8deg);
  transform-origin: center bottom;
  overflow: hidden;
}

.landing-preview-bar {
  display: flex;
  gap: 6px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-color);
  background: rgba(1, 4, 9, 0.9);
}

.landing-preview-bar span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #30363d;
}

.landing-preview-body {
  display: flex;
  min-height: 220px;
}

.landing-preview-sidebar {
  width: 18%;
  border-right: 1px solid var(--border-color);
  background: rgba(1, 4, 9, 0.6);
}

.landing-preview-main {
  flex: 1;
  padding: 24px 28px;
}

.landing-preview-line {
  height: 10px;
  width: 55%;
  border-radius: 4px;
  background: rgba(48, 54, 61, 0.8);
  margin-bottom: 12px;
}

.landing-preview-line--wide {
  width: 72%;
  margin-bottom: 18px;
}

.landing-preview-chart {
  margin-top: 20px;
  height: 100px;
  border-radius: 8px;
  border: 1px solid rgba(56, 139, 253, 0.2);
  background: linear-gradient(
    135deg,
    rgba(56, 139, 253, 0.08) 0%,
    rgba(13, 17, 23, 0.4) 50%,
    rgba(56, 139, 253, 0.05) 100%
  );
}

@media (max-width: 640px) {
  .landing-hero {
    margin-top: 48px;
  }

  .landing-preview {
    margin-top: 40px;
  }

  .landing-preview-window {
    transform: none;
  }
}
"""

p.write_text(text[:start] + new_css + "\n", encoding="utf-8")
print("reverted")
