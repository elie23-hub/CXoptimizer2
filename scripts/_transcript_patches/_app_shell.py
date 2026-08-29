from pathlib import Path

p = Path(__file__).parent / "style.css"
text = p.read_text(encoding="utf-8")

replacements = [
(
"html:has(body.landing-body) {\n  height: 100%;\n}",
"html:has(body.landing-body),\nhtml:has(body.app-body) {\n  height: 100%;\n}",
),
(
"body.landing-body {\n  display: block;\n  width: 100%;\n  min-height: 100vh;\n  height: 100vh;\n  margin: 0;\n  background: #08090d;\n  overflow: hidden;\n  font-family: \"Inter\", system-ui, -apple-system, sans-serif;\n}\n\n.landing-page {",
"body.landing-body {\n  display: block;\n  width: 100%;\n  min-height: 100vh;\n  height: 100vh;\n  margin: 0;\n  background: #08090d;\n  overflow: hidden;\n  font-family: \"Inter\", system-ui, -apple-system, sans-serif;\n}\n\nbody.app-body {\n  display: block;\n  width: 100%;\n  min-height: 100vh;\n  margin: 0;\n  background: #08090d;\n  color: var(--text-primary);\n  font-family: \"Inter\", system-ui, -apple-system, sans-serif;\n}\n\n.site-page,\n.landing-page {",
),
(
".landing-page {\n  position: relative;\n  width: 100%;\n  min-height: 100vh;\n  height: 100vh;\n  display: flex;\n  flex-direction: column;\n  align-items: center;\n  padding: 0 32px 28px;\n  overflow: hidden;\n}",
""".site-page,
.landing-page {
  position: relative;
  width: 100%;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0 32px 28px;
}

body.landing-body .site-page,
body.landing-body .landing-page {
  height: 100vh;
  overflow: hidden;
}

body.app-body .site-page--app {
  min-height: 100vh;
  height: auto;
  overflow: visible;
  padding-bottom: 40px;
}""",
),
(
".landing-nav-links a:hover {\n  color: #e8eaed;\n}",
""".landing-nav-links a:hover {
  color: #e8eaed;
}

.landing-nav-links a.is-active {
  color: #e8eaed;
  text-decoration: underline;
  text-underline-offset: 6px;
  text-decoration-thickness: 1px;
}""",
),
(
".main-wrapper {\n  margin-left: var(--sidebar-width);\n  flex: 1;\n  display: flex;\n  flex-direction: column;\n  min-height: 100vh;\n  min-width: 0;\n  max-width: calc(100vw - var(--sidebar-width));\n  overflow-x: hidden;\n}",
""".main-wrapper {
  margin-left: var(--sidebar-width);
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  min-width: 0;
  max-width: calc(100vw - var(--sidebar-width));
  overflow-x: hidden;
}

body.app-body .main-wrapper {
  position: relative;
  z-index: 2;
  width: 100%;
  max-width: 1120px;
  margin: 0 auto;
  min-height: calc(100vh - 80px);
}

body.app-body .top-header {
  background: transparent;
  border-bottom: none;
  padding: 4px 0 18px;
}

body.app-body .main-content {
  padding-top: 0;
}""",
),
]

for old, new in replacements:
    if old not in text:
        raise SystemExit(f"block not found:\n{old[:120]}...")
    text = text.replace(old, new, 1)

p.write_text(text, encoding="utf-8")
print("ok")
