from pathlib import Path

p = Path(__file__).parent / "style.css"
text = p.read_text(encoding="utf-8")
start = text.find("/* ---------- Landing page ---------- */")
if start == -1:
    raise SystemExit("start not found")

new_css = r"""/* ---------- Landing page ---------- */
html:has(body.landing-body) {
  height: 100%;
}

body.landing-body {
  display: block;
  width: 100%;
  min-height: 100vh;
  height: 100vh;
  margin: 0;
  background: #08090d;
  overflow: hidden;
  font-family: "Inter", system-ui, -apple-system, sans-serif;
}

.landing-page {
  position: relative;
  width: 100%;
  min-height: 100vh;
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 32px 28px;
  overflow: hidden;
}

.landing-bg-curve {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(ellipse 55% 45% at 18% 22%, rgba(88, 120, 255, 0.42) 0%, transparent 58%),
    radial-gradient(ellipse 40% 35% at 72% 68%, rgba(120, 80, 220, 0.18) 0%, transparent 55%),
    linear-gradient(135deg, rgba(60, 100, 255, 0.12) 0%, transparent 42%, rgba(90, 60, 180, 0.08) 100%);
  z-index: 0;
}

.landing-bg-curve::before {
  content: "";
  position: absolute;
  top: -10%;
  left: -8%;
  width: 72%;
  height: 85%;
  background: linear-gradient(
    118deg,
    rgba(130, 160, 255, 0.55) 0%,
    rgba(100, 130, 255, 0.28) 28%,
    rgba(80, 100, 200, 0.08) 52%,
    transparent 72%
  );
  filter: blur(40px);
  transform: rotate(-8deg);
  border-radius: 40% 60% 50% 50%;
}

.landing-bg-grid {
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.35;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px);
  background-size: 80px 80px;
  mask-image: radial-gradient(ellipse 80% 70% at 50% 40%, black 20%, transparent 75%);
  z-index: 0;
}

.landing-bg-shapes {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background:
    linear-gradient(32deg, transparent 48%, rgba(255, 255, 255, 0.06) 49%, rgba(255, 255, 255, 0.06) 49.5%, transparent 51%) 12% 18% / 180px 180px no-repeat,
    linear-gradient(-18deg, transparent 48%, rgba(255, 255, 255, 0.05) 49%, transparent 51%) 78% 28% / 140px 140px no-repeat,
    linear-gradient(55deg, transparent 48%, rgba(255, 255, 255, 0.04) 49%, transparent 51%) 65% 72% / 120px 120px no-repeat;
}

.landing-bg-shapes::before,
.landing-bg-shapes::after {
  content: "";
  position: absolute;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.02);
}

.landing-bg-shapes::before {
  width: 52px;
  height: 52px;
  top: 22%;
  right: 18%;
  transform: rotate(12deg);
}

.landing-bg-shapes::after {
  width: 36px;
  height: 36px;
  bottom: 32%;
  left: 14%;
  transform: rotate(-8deg);
}

.landing-nav {
  position: relative;
  z-index: 3;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  width: 100%;
  max-width: 1120px;
  padding: 22px 0 0;
  flex-shrink: 0;
}

.landing-nav-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: #e8eaed;
  font-size: 15px;
  font-weight: 600;
  text-decoration: none;
  justify-self: start;
}

.landing-nav-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #8ab4ff;
  font-size: 14px;
}

.landing-nav-links {
  display: flex;
  align-items: center;
  gap: 28px;
  justify-self: center;
}

.landing-nav-links a {
  color: #9aa0a6;
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  transition: color 0.15s ease;
}

.landing-nav-links a:hover {
  color: #e8eaed;
}

.landing-nav-cta {
  justify-self: end;
  padding: 9px 18px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #e8eaed;
  font-size: 13px;
  font-weight: 500;
  text-decoration: none;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.landing-nav-cta:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
}

.landing-hero {
  position: relative;
  z-index: 2;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  width: 100%;
  max-width: 780px;
  margin: 0 auto;
  padding: 24px 12px;
}

.landing-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.04);
  color: #c4c8cc;
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 28px;
}

.landing-badge-icon {
  color: #8ab4ff;
  font-size: 11px;
}

.landing-title {
  margin: 0 0 22px;
  font-size: clamp(2.2rem, 5vw, 3.4rem);
  font-weight: 600;
  line-height: 1.15;
  letter-spacing: -0.035em;
  color: #b8bcc4;
}

.landing-subtitle {
  margin: 0 auto 36px;
  max-width: 580px;
  font-size: clamp(0.92rem, 1.8vw, 1.02rem);
  line-height: 1.7;
  color: #6e7378;
  font-weight: 400;
}

.landing-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 14px;
}

.landing-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 148px;
  padding: 13px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.landing-btn--primary {
  background: rgba(18, 20, 26, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.14);
  color: #e8eaed;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
}

.landing-btn--primary:hover {
  background: rgba(28, 30, 38, 0.95);
  border-color: rgba(255, 255, 255, 0.22);
}

.landing-btn--ghost {
  background: transparent;
  border: 1px solid transparent;
  color: #9aa0a6;
}

.landing-btn--ghost:hover {
  color: #e8eaed;
}

.landing-trust {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 900px;
  text-align: center;
  flex-shrink: 0;
  padding-top: 8px;
}

.landing-trust-label {
  margin: 0 0 18px;
  font-size: 12px;
  color: #5f6368;
  font-weight: 400;
}

.landing-logos {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 28px 36px;
}

.landing-logos span {
  font-size: 13px;
  font-weight: 600;
  color: #4a4e54;
  letter-spacing: 0.02em;
  opacity: 0.85;
}

@media (max-width: 768px) {
  .landing-page {
    padding: 0 20px 20px;
  }

  .landing-nav {
    grid-template-columns: 1fr auto;
    gap: 12px;
  }

  .landing-nav-links {
    display: none;
  }

  .landing-nav-cta {
    justify-self: end;
  }

  .landing-title {
    font-size: 2rem;
  }

  .landing-subtitle {
    margin-bottom: 28px;
  }

  .landing-logos {
    gap: 20px 24px;
  }

  .landing-logos span {
    font-size: 11px;
  }
}

@media (max-width: 480px) {
  .landing-actions {
    flex-direction: column;
    width: 100%;
    max-width: 280px;
  }

  .landing-btn {
    width: 100%;
  }
}
"""

p.write_text(text[:start] + new_css + "\n", encoding="utf-8")
print("ok")
