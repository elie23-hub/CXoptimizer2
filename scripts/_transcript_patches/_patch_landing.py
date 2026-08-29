from pathlib import Path

p = Path(__file__).parent / "style.css"
text = p.read_text(encoding="utf-8")
start = text.find("/* ---------- Landing page ---------- */")
if start == -1:
    raise SystemExit("start not found")

new_css = r"""/* ---------- Landing page ---------- */
body.landing-body {
  display: block;
  height: 100vh;
  max-height: 100vh;
  background: #03050c;
  overflow: hidden;
}

.landing-page {
  position: relative;
  height: 100vh;
  max-height: 100vh;
  overflow: hidden;
}

.landing-horizon {
  position: absolute;
  top: 14%;
  left: 50%;
  width: 200%;
  height: 55%;
  transform: translateX(-50%);
  border-radius: 50%;
  pointer-events: none;
  background: radial-gradient(
    ellipse 48% 40% at 50% 0%,
    rgba(180, 210, 255, 0.7) 0%,
    rgba(100, 160, 255, 0.35) 18%,
    rgba(56, 139, 253, 0.15) 38%,
    rgba(31, 111, 235, 0.05) 55%,
    transparent 72%
  );
  filter: blur(6px);
  z-index: 0;
}

.landing-glow {
  position: absolute;
  pointer-events: none;
  border-radius: 50%;
}

.landing-glow--top {
  top: -48%;
  left: 50%;
  width: 150%;
  height: 78%;
  transform: translateX(-50%);
  background: radial-gradient(
    ellipse at center,
    rgba(56, 139, 253, 0.28) 0%,
    rgba(31, 111, 235, 0.1) 40%,
    transparent 72%
  );
}

.landing-glow--floor {
  bottom: 0;
  left: 50%;
  width: 130%;
  height: 45%;
  transform: translateX(-50%);
  background: radial-gradient(
    ellipse at center,
    rgba(56, 139, 253, 0.22) 0%,
    transparent 68%
  );
}

.landing-stars {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    radial-gradient(1px 1px at 12% 18%, rgba(255, 255, 255, 0.4), transparent),
    radial-gradient(1px 1px at 28% 62%, rgba(255, 255, 255, 0.28), transparent),
    radial-gradient(1px 1px at 54% 12%, rgba(255, 255, 255, 0.35), transparent),
    radial-gradient(1px 1px at 70% 38%, rgba(255, 255, 255, 0.22), transparent),
    radial-gradient(1px 1px at 86% 72%, rgba(255, 255, 255, 0.3), transparent),
    radial-gradient(1px 1px at 20% 82%, rgba(255, 255, 255, 0.25), transparent);
}

.landing-hero {
  position: relative;
  z-index: 2;
  text-align: center;
  max-width: 720px;
  margin: 0 auto;
  padding: 12vh 24px 0;
}

.landing-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 16px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
  color: #c9d1d9;
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.01em;
  margin-bottom: 28px;
}

.landing-badge-icon {
  color: #79c0ff;
  font-size: 11px;
}

.landing-title {
  margin: 0 0 22px;
  font-size: 3.5rem;
  font-weight: 700;
  line-height: 1.08;
  letter-spacing: -0.045em;
  color: #ffffff;
}

.landing-subtitle {
  margin: 0 auto 34px;
  max-width: 520px;
  font-size: 15px;
  line-height: 1.75;
  color: #8b949e;
  font-weight: 400;
}

.landing-cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 132px;
  padding: 12px 28px;
  border-radius: 999px;
  background: #f0f3f8;
  color: #0d1117;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.1),
    0 4px 24px rgba(56, 139, 253, 0.28);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.landing-cta:hover {
  transform: translateY(-1px);
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.14),
    0 8px 32px rgba(56, 139, 253, 0.38);
}

.landing-preview-scene {
  position: absolute;
  left: 50%;
  bottom: -12%;
  z-index: 1;
  width: min(1180px, 96vw);
  height: 64vh;
  transform: translateX(-50%);
  perspective: 1200px;
  perspective-origin: 50% 100%;
  pointer-events: none;
}

.landing-preview {
  width: 100%;
  height: 100%;
  transform-style: preserve-3d;
  transform: rotateX(24deg) scale(1.04);
  transform-origin: center bottom;
}

.landing-preview-window {
  width: 100%;
  min-height: 500px;
  border-radius: 14px 14px 0 0;
  border: 1px solid rgba(56, 139, 253, 0.35);
  border-bottom: none;
  background: rgba(10, 14, 22, 0.94);
  box-shadow:
    0 -24px 90px rgba(56, 139, 253, 0.32),
    0 48px 140px rgba(0, 0, 0, 0.7),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
  overflow: hidden;
  backface-visibility: hidden;
}

.landing-preview-bar {
  display: flex;
  gap: 6px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-color);
  background: rgba(1, 4, 9, 0.95);
}

.landing-preview-bar span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #30363d;
}

.landing-preview-body {
  display: flex;
  min-height: 420px;
}

.lp-dash-sidebar {
  width: 148px;
  flex-shrink: 0;
  border-right: 1px solid var(--border-color);
  background: #010409;
  padding: 14px 10px;
}

.lp-dash-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 8px 12px;
  margin-bottom: 10px;
  border-bottom: 1px solid var(--border-color);
  font-size: 11px;
  font-weight: 600;
  color: var(--text-primary);
}

.lp-dash-brand-icon {
  color: var(--accent-blue);
  font-size: 14px;
}

.lp-dash-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.lp-dash-nav-item {
  display: block;
  padding: 7px 10px;
  border-radius: 6px;
  font-size: 10px;
  color: var(--text-secondary);
}

.lp-dash-nav-item.is-active {
  background: rgba(56, 139, 253, 0.12);
  color: #79c0ff;
}

.lp-dash-main {
  flex: 1;
  min-width: 0;
  padding: 14px 16px 16px;
  background: #0d1117;
}

.lp-dash-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.lp-dash-page-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.lp-dash-file-badge {
  padding: 3px 8px;
  border-radius: 999px;
  background: #21262d;
  border: 1px solid var(--border-color);
  font-size: 9px;
  color: var(--text-secondary);
}

.lp-dash-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: #161b22;
}

.lp-dash-pill {
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  background: #21262d;
  font-size: 9px;
  color: var(--text-secondary);
}

.lp-dash-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.lp-dash-stat {
  padding: 10px 8px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: #161b22;
  text-align: center;
}

.lp-dash-stat strong {
  display: block;
  font-size: 16px;
  line-height: 1.1;
  color: var(--text-primary);
}

.lp-dash-stat span {
  display: block;
  margin-top: 4px;
  font-size: 8px;
  color: var(--text-muted);
}

.lp-dash-stat--urgent strong {
  color: var(--error-red);
}

.lp-dash-row {
  display: grid;
  grid-template-columns: 1.35fr 0.9fr;
  gap: 10px;
  margin-bottom: 10px;
}

.lp-dash-card {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: #161b22;
  padding: 10px;
  min-width: 0;
}

.lp-dash-card-title {
  margin: 0 0 8px;
  font-size: 10px;
  font-weight: 600;
  color: var(--text-primary);
}

.lp-dash-biplot {
  display: block;
  width: 100%;
  height: auto;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  background: #0d1117;
}

.lp-dash-priority-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.lp-dash-priority-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 9px;
  color: var(--text-secondary);
  line-height: 1.35;
}

.lp-dash-priority-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.lp-dash-priority-dot.urgent {
  background: #990000;
}

@media (max-width: 900px) {
  .landing-title {
    font-size: 2.65rem;
  }

  .landing-hero {
    padding-top: 10vh;
  }

  .landing-preview-scene {
    width: 98vw;
    height: 54vh;
    bottom: -10%;
  }

  .landing-preview {
    transform: rotateX(18deg) scale(1.02);
  }
}

@media (max-width: 640px) {
  .landing-title {
    font-size: 2rem;
  }

  .landing-subtitle {
    font-size: 14px;
    margin-bottom: 26px;
  }

  .landing-preview-scene {
    height: 46vh;
    bottom: -8%;
  }

  .landing-preview {
    transform: rotateX(14deg) scale(1);
  }

  .lp-dash-stats {
    grid-template-columns: repeat(2, 1fr);
  }

  .lp-dash-row {
    grid-template-columns: 1fr;
  }

  .lp-dash-sidebar {
    width: 96px;
  }
}
"""

p.write_text(text[:start] + new_css + "\n", encoding="utf-8")
print("patched", len(new_css))
