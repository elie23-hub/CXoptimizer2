/**
 * Simulation — bottom-up mode (process scores → predicted overall satisfaction).
 */

(function () {
  const promptEl = document.getElementById("sim-prompt");
  const promptText = document.getElementById("sim-prompt-text");
  const errorEl = document.getElementById("sim-error");
  const errorText = document.getElementById("sim-error-text");
  const workspaceEl = document.getElementById("sim-workspace");
  const osatPanelEl = document.getElementById("sim-osat-panel");
  const osatSpacerEl = document.getElementById("sim-osat-spacer");
  const gaugeEl = document.getElementById("sim-osat-gauge");
  const gaugeCanvas = document.getElementById("sim-gauge-canvas");
  const listEl = document.getElementById("sim-statements-list");
  const predictedEl = document.getElementById("sim-predicted-overall");
  const baselineEl = document.getElementById("sim-baseline-overall");
  const deltaBadge = document.getElementById("sim-delta-badge");
  const deltaText = document.getElementById("sim-delta-text");
  const statusDetail = document.getElementById("sim-status-detail");
  const statusModel = document.getElementById("sim-status-model");
  const resetScoresBtn = document.getElementById("sim-reset-scores");
  const setAll100Btn = document.getElementById("sim-set-all-100");
  const statusLeft = document.getElementById("sim-status-left");
  const modeHintBottom = document.getElementById("sim-mode-hint");
  const modeHintTop = document.getElementById("sim-mode-hint-topdown");
  const topdownEl = document.getElementById("sim-topdown");
  const tdTargetInput = document.getElementById("sim-td-target");
  const tdResultsEl = document.getElementById("sim-td-results");
  const tdListEl = document.getElementById("sim-td-list");
  const tdAchievedEl = document.getElementById("sim-td-achieved");
  const tdQuadrantInputs = document.querySelectorAll(
    'input[name="sim-td-quadrant"]'
  );
  const tdBiplotCard = document.getElementById("sim-td-biplot-card");
  const tdWorkspaceEl = document.getElementById("sim-td-workspace");
  const tdBiplotEl = document.getElementById("sim-td-biplot");
  const tdBiplotResetBtn = document.getElementById("sim-td-biplot-reset");
  const tdBiplotFullscreenBtn = document.getElementById(
    "sim-td-biplot-fullscreen"
  );
  const modeButtons = document.querySelectorAll(".sim-mode-btn[data-mode]");
  const buExportXlsxBtn = document.getElementById("sim-bu-export-xlsx");
  const tdExportXlsxBtn = document.getElementById("sim-td-export-xlsx");

  if (!listEl) return;



  let meta = null;
  let scores = {};
  let originalScores = {};
  let predictTimer = null;
  let predictSeq = 0;
  let gaugeValue = 0;
  let gaugeAnimFrame = null;
  let gaugeIntroDone = false;
  let sectionGaugesIntroDone = false;
  let gaugeCanvasDpr = 0;
  const canvasDprMap = new WeakMap();
  const sectionGaugeState = {};
  let simMode = "bottom-up";
  let tdOptionIndex = 0;
  let tdSolveTimer = null;
  let tdReady = false;
  let tdBiplotFollowSolve = false;
  let tdBiplotAxisRange = null;
  const SUMMARY_STORAGE_KEY = "gapAnalyzer_sim_summary";

  const TD_QUADRANT_THEME = {
    maintain: {
      fill: "rgba(217, 234, 211, 0.85)",
      dot: "#38761d",
      quadrantLabel: "#2d5a1a",
      label: "High Performance High Importance",
    },
    low: {
      fill: "rgba(255, 242, 204, 0.9)",
      dot: "#bf9000",
      quadrantLabel: "#8a6800",
      label: "Low Performance Low Importance",
    },
    urgent: {
      fill: "rgba(244, 204, 204, 0.9)",
      dot: "#990000",
      quadrantLabel: "#7a1010",
      label: "Low Performance High Importance",
    },
    overkill: {
      fill: "rgba(207, 226, 243, 0.9)",
      dot: "#1155cc",
      quadrantLabel: "#0d3f96",
      label: "High Performance Low Importance",
    },
  };

  const TD_BIPLOT_ORDER = ["urgent", "maintain", "low", "overkill"];
  const TD_BIPLOT_CONFIG = {
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    scrollZoom: true,
    modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"],
    toImageButtonOptions: {
      format: "png",
      filename: "simulation-topdown-biplot",
      scale: 2,
    },
  };

  function persistSummaryState(extra) {
    try {
      let previous = {};
      try {
        previous = JSON.parse(sessionStorage.getItem(SUMMARY_STORAGE_KEY) || "{}") || {};
      } catch (e) {
        previous = {};
      }
      const payload = Object.assign({}, previous, {
        bottom_up_scores: scores,
        target_overall:
          (tdTargetInput && tdTargetInput.value) ||
          previous.target_overall ||
          null,
        top_down_option_index: tdOptionIndex || 0,
        saved_at: Date.now(),
      }, extra || {});
      sessionStorage.setItem(SUMMARY_STORAGE_KEY, JSON.stringify(payload));
    } catch (e) {
      /* ignore quota / private mode */
    }
  }

  function buildBottomUpChangedRows() {
    if (!meta) return [];
    const rows = [];
    (meta.statements || []).forEach(function (s) {
      const col = s.column;
      const from = Number(s.performance);
      const to = scores[col] != null ? Number(scores[col]) : from;
      if (!Number.isFinite(from) || !Number.isFinite(to)) return;
      if (Math.round(from) === Math.round(to)) return;
      rows.push({
        column: col,
        label: s.label || col,
        section: s.section,
        section_name: s.section_name,
        quadrant: s.quadrant || "low",
        performance: Math.round(from * 10) / 10,
        required_performance: Math.round(to * 10) / 10,
        delta_pts: Math.round((to - from) * 10) / 10,
        changed: true,
      });
    });
    return rows;
  }

  function buildTopDownChangedRows(data) {
    const option = (data && data.option) || {};
    return ((option.statements || []).filter(function (row) {
      return !!row.changed;
    })).map(function (row) {
      return {
        column: row.column,
        label: row.label,
        section: row.section,
        section_name: row.section_name,
        quadrant: row.quadrant,
        performance: row.performance,
        required_performance: row.required_performance,
        delta_pts: row.delta_pts,
        changed: true,
        eligible: row.eligible,
      };
    });
  }

  const prefersReducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const GAUGE = {
    width: 320,
    height: 200,
    radius: 118,
    lineWidth: 22,
    pivotYOffset: 28,
    colors: {
      fillStart: "#3d4f7a",
      fillEnd: "#1b254a",
      empty: "rgba(27, 37, 74, 0.12)",
      needle: "#1b254a",
      needleTip: "#24325f",
      pivot: "#1b254a",
      pivotRing: "rgba(27, 37, 74, 0.2)",
    },
  };

  const SECTION_GAUGE = {
    width: 168,
    height: 108,
    radius: 62,
    lineWidth: 11,
    pivotYOffset: 16,
    colors: GAUGE.colors,
  };

  let osatPinnedToBody = false;

  function getSimScrollRoot() {
    const wrap = document.querySelector(".main-wrapper");
    if (wrap && wrap.scrollHeight > wrap.clientHeight + 8) return wrap;
    return null;
  }

  function getOsatPinMetrics() {
    const wrap = document.querySelector(".main-wrapper");
    if (wrap) {
      const rect = wrap.getBoundingClientRect();
      return {
        left: rect.left,
        width: rect.width,
      };
    }
    return { left: 0, width: window.innerWidth };
  }

  function restoreOsatPanelHome() {
    if (!osatPanelEl || !osatPinnedToBody || !osatSpacerEl || !osatSpacerEl.parentNode) {
      osatPinnedToBody = false;
      return;
    }
    osatSpacerEl.parentNode.insertBefore(osatPanelEl, osatSpacerEl);
    osatPinnedToBody = false;
  }

  function releaseOsatPinLayout() {
    if (!osatPanelEl) return;
    osatPanelEl.classList.remove("is-scrolled", "is-fixed");
    osatPanelEl.style.top = "";
    osatPanelEl.style.left = "";
    osatPanelEl.style.width = "";
    restoreOsatPanelHome();
    if (osatSpacerEl) {
      osatSpacerEl.classList.remove("is-active");
      osatSpacerEl.style.height = "";
    }
    document.documentElement.style.setProperty("--sim-osat-pin-offset", "16px");
  }

  function setOsatPanelVisible(visible) {
    if (!osatPanelEl) return;
    osatPanelEl.hidden = !visible;
    if (!visible) {
      releaseOsatPinLayout();
      return;
    }
    requestAnimationFrame(function () {
      updateOsatFixedScroll();
    });
    if (!gaugeIntroDone) {
      gaugeValue = 0;
      if (predictedEl) predictedEl.textContent = formatPct(0);
      drawGauge(0);
      setGaugeAria(0);
      return;
    }
    drawGauge(gaugeValue);
  }

  function updateOsatFixedScroll() {
    if (!osatPanelEl || osatPanelEl.hidden) {
      releaseOsatPinLayout();
      return;
    }

    const alreadyFixed = osatPanelEl.classList.contains("is-fixed");
    const probe = alreadyFixed && osatSpacerEl ? osatSpacerEl : osatPanelEl;
    const stuck = probe.getBoundingClientRect().top <= 1;

    if (!stuck) {
      releaseOsatPinLayout();
      return;
    }

    if (osatSpacerEl) {
      if (!alreadyFixed) {
        osatSpacerEl.style.height = osatPanelEl.offsetHeight + "px";
      }
      osatSpacerEl.classList.add("is-active");
    }

    if (osatPanelEl.parentElement !== document.body && osatSpacerEl) {
      document.body.appendChild(osatPanelEl);
      osatPinnedToBody = true;
      drawGaugeOnCanvas(gaugeCanvas, gaugeValue, GAUGE);
    }

    const metrics = getOsatPinMetrics();
    osatPanelEl.classList.add("is-scrolled", "is-fixed");
    osatPanelEl.style.top = "0px";
    osatPanelEl.style.left = Math.round(metrics.left) + "px";
    osatPanelEl.style.width = Math.round(metrics.width) + "px";

    const height = osatPanelEl.offsetHeight;
    if (osatSpacerEl) {
      osatSpacerEl.style.height = height + "px";
    }

    document.documentElement.style.setProperty(
      "--sim-osat-pin-offset",
      height + 12 + "px"
    );
  }

  function bindOsatScrollListeners() {
    const root = document.querySelector(".main-wrapper");
    if (root) {
      root.addEventListener("scroll", updateOsatFixedScroll, { passive: true });
    }
    window.addEventListener("scroll", updateOsatFixedScroll, { passive: true, capture: true });
    document.addEventListener("scroll", updateOsatFixedScroll, { passive: true, capture: true });
    window.addEventListener("resize", updateOsatFixedScroll);
  }

  bindOsatScrollListeners();

  function gaugeGeometry(spec) {
    const cx = spec.width / 2;
    const cy = spec.height - spec.pivotYOffset;
    return { cx: cx, cy: cy, radius: spec.radius };
  }

  /** Map 0–100% to canvas arc angle: π (left) → 3π/2 (top) → 2π (right). */
  function valueToAngle(pct) {
    const v = Math.max(0, Math.min(100, Number(pct) || 0));
    return Math.PI + (v / 100) * Math.PI;
  }

  function pointOnArc(cx, cy, radius, angle) {
    return {
      x: cx + Math.cos(angle) * radius,
      y: cy + Math.sin(angle) * radius,
    };
  }

  function drawArcEndCap(ctx, cx, cy, radius, angle, color, lw) {
    const p = pointOnArc(cx, cy, radius, angle);
    ctx.beginPath();
    ctx.arc(p.x, p.y, lw / 2, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
  }

  function ensureGaugeCanvasSize(ctx, canvas, spec, useGlobalDpr) {
    const dpr = window.devicePixelRatio || 1;
    const w = spec.width;
    const h = spec.height;
    const prev = useGlobalDpr ? gaugeCanvasDpr : canvasDprMap.get(canvas);
    if (useGlobalDpr) {
      if (gaugeCanvasDpr !== dpr || canvas.width !== Math.round(w * dpr)) {
        canvas.width = Math.round(w * dpr);
        canvas.height = Math.round(h * dpr);
        canvas.style.width = w + "px";
        canvas.style.height = h + "px";
        gaugeCanvasDpr = dpr;
      }
    } else if (!prev || prev !== dpr || canvas.width !== Math.round(w * dpr)) {
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      canvas.style.width = w + "px";
      canvas.style.height = h + "px";
      canvasDprMap.set(canvas, dpr);
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function drawGaugeOnCanvas(canvas, pct, spec) {
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const useGlobalDpr = canvas === gaugeCanvas;
    ensureGaugeCanvasSize(ctx, canvas, spec, useGlobalDpr);

    const w = spec.width;
    const h = spec.height;
    ctx.clearRect(0, 0, w, h);

    const v = Math.max(0, Math.min(100, Number(pct) || 0));
    const { cx, cy, radius } = gaugeGeometry(spec);
    const startAngle = Math.PI;
    const endAngle = 2 * Math.PI;
    const valueAngle = valueToAngle(v);
    const lw = spec.lineWidth;
    const arcAnticlockwise = false;
    const colors = spec.colors || GAUGE.colors;

    ctx.lineCap = "butt";
    ctx.lineJoin = "round";

    const fillGrad = ctx.createLinearGradient(cx - radius, cy, cx + radius, cy - radius);
    fillGrad.addColorStop(0, colors.fillStart);
    fillGrad.addColorStop(1, colors.fillEnd);

    if (v < 99.5) {
      ctx.beginPath();
      ctx.arc(cx, cy, radius, valueAngle, endAngle, arcAnticlockwise);
      ctx.strokeStyle = colors.empty;
      ctx.lineWidth = lw;
      ctx.stroke();
    }

    if (v > 0.5) {
      ctx.beginPath();
      ctx.arc(cx, cy, radius, startAngle, valueAngle, arcAnticlockwise);
      ctx.strokeStyle = fillGrad;
      ctx.lineWidth = lw;
      ctx.stroke();
    }

    if (v <= 0.5) {
      ctx.beginPath();
      ctx.arc(cx, cy, radius, startAngle, endAngle, arcAnticlockwise);
      ctx.strokeStyle = colors.empty;
      ctx.lineWidth = lw;
      ctx.stroke();
    }

    const leftCapColor = v > 0.5 ? colors.fillEnd : colors.empty;
    const rightCapColor = v >= 99.5 ? colors.fillEnd : colors.empty;
    drawArcEndCap(ctx, cx, cy, radius, startAngle, leftCapColor, lw);
    drawArcEndCap(ctx, cx, cy, radius, endAngle, rightCapColor, lw);
    if (v > 0.5 && v < 99.5) {
      drawArcEndCap(ctx, cx, cy, radius, valueAngle, colors.fillEnd, lw);
    }

    const needleLen = radius - lw / 2 - 2;
    const tip = pointOnArc(cx, cy, needleLen, valueAngle);
    const perp = valueAngle + Math.PI / 2;
    const baseHalf = spec === SECTION_GAUGE ? 5 : 8;
    const b1 = {
      x: cx + Math.cos(perp) * baseHalf,
      y: cy + Math.sin(perp) * baseHalf,
    };
    const b2 = {
      x: cx - Math.cos(perp) * baseHalf,
      y: cy - Math.sin(perp) * baseHalf,
    };

    const needleGrad = ctx.createLinearGradient(cx, cy, tip.x, tip.y);
    needleGrad.addColorStop(0, colors.needle);
    needleGrad.addColorStop(1, colors.needleTip);
    ctx.beginPath();
    ctx.moveTo(tip.x, tip.y);
    ctx.lineTo(b1.x, b1.y);
    ctx.lineTo(b2.x, b2.y);
    ctx.closePath();
    ctx.fillStyle = needleGrad;
    ctx.fill();

    const pivotR = spec === SECTION_GAUGE ? 7 : 12;
    ctx.beginPath();
    ctx.arc(cx, cy, pivotR, 0, Math.PI * 2);
    ctx.fillStyle = colors.pivot;
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = colors.pivotRing;
    ctx.stroke();
  }

  function drawGauge(pct) {
    drawGaugeOnCanvas(gaugeCanvas, pct, GAUGE);
    if (osatPanelEl && !osatPanelEl.hidden) {
      updateOsatFixedScroll();
    }
  }

  function gaugeEase(t, intro) {
    if (intro) {
      return 1 - Math.pow(1 - t, 4);
    }
    return 1 - Math.pow(1 - t, 3);
  }

  function setGaugeAria(pct) {
    if (!gaugeEl) return;
    gaugeEl.style.setProperty("--osat-pct", String(pct));
    gaugeEl.setAttribute("aria-valuenow", String(Math.round(pct)));
  }

  function updateGauge(pct, options) {
    const opts = options || {};
    const target = Math.max(0, Math.min(100, Number(pct) || 0));
    const intro = !!opts.intro && !prefersReducedMotion;
    const from = intro ? 0 : gaugeValue;

    if (!gaugeCanvas) {
      gaugeValue = target;
      setGaugeAria(target);
      return;
    }

    if (gaugeAnimFrame) cancelAnimationFrame(gaugeAnimFrame);

    if (prefersReducedMotion || (!intro && Math.abs(target - from) < 0.25)) {
      gaugeValue = target;
      drawGauge(gaugeValue);
      setGaugeAria(target);
      if (predictedEl && opts.updateLabel !== false) {
        predictedEl.textContent = formatPct(target);
      }
      if (intro) gaugeIntroDone = true;
      return;
    }

    const duration = intro ? 1650 : 480;
    const start = performance.now();

    function frame(now) {
      const t = Math.min(1, (now - start) / duration);
      const eased = gaugeEase(t, intro);
      gaugeValue = from + (target - from) * eased;
      drawGauge(gaugeValue);
      setGaugeAria(gaugeValue);
      if (predictedEl && opts.updateLabel !== false) {
        predictedEl.textContent = formatPct(gaugeValue);
      }
      if (t < 1) {
        gaugeAnimFrame = requestAnimationFrame(frame);
      } else {
        gaugeValue = target;
        gaugeAnimFrame = null;
        if (intro) gaugeIntroDone = true;
        if (predictedEl) predictedEl.textContent = formatPct(target);
        setGaugeAria(target);
      }
    }

    gaugeAnimFrame = requestAnimationFrame(frame);
  }

  window.addEventListener("resize", function () {
    gaugeCanvasDpr = 0;
    if (osatPanelEl && !osatPanelEl.hidden) drawGauge(gaugeValue);
    Object.keys(sectionGaugeState).forEach(function (key) {
      const state = sectionGaugeState[key];
      if (state && state.canvas) {
        canvasDprMap.delete(state.canvas);
        drawGaugeOnCanvas(state.canvas, state.gaugeValue, SECTION_GAUGE);
      }
    });
  });

  function showError(msg, isWarning) {
    if (errorEl && errorText) {
      errorEl.classList.toggle("is-warning", !!isWarning);
      errorText.textContent = msg;
      errorEl.hidden = false;
    }
    if (workspaceEl) workspaceEl.hidden = true;
    if (topdownEl) topdownEl.hidden = true;
    if (promptEl) promptEl.hidden = true;
    setOsatPanelVisible(false);
  }

  function hideError() {
    if (errorEl) {
      errorEl.hidden = true;
      errorEl.classList.remove("is-warning");
    }
  }

  function showPrompt(msg) {
    hideError();
    if (promptText) promptText.innerHTML = msg;
    if (promptEl) promptEl.hidden = false;
    if (workspaceEl) workspaceEl.hidden = true;
    if (topdownEl) topdownEl.hidden = true;
    if (modeHintBottom) modeHintBottom.hidden = true;
    if (modeHintTop) modeHintTop.hidden = true;
    setOsatPanelVisible(false);
    tdReady = false;
  }

  function escapeHtml(str) {
    return String(str == null ? "" : str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  async function readJsonResponse(res) {
    const text = await res.text();
    try {
      return JSON.parse(text);
    } catch (parseErr) {
      const trimmed = text.trim().toLowerCase();
      if (trimmed.startsWith("<!doctype") || trimmed.startsWith("<html")) {
        throw new Error(
          "Server returned a web page instead of JSON. Restart Flask (python app.py) so the simulation routes are loaded."
        );
      }
      throw new Error("Invalid response from server.");
    }
  }

  function formatPct(val) {
    const n = Number(val);
    if (Number.isNaN(n)) return "—";
    return Math.round(n) + "%";
  }

  function sectionLabel(stmt) {
    if (stmt.section_name) return stmt.section_name;
    if (stmt.section != null && stmt.section !== "") return "Section " + stmt.section;
    return "Other";
  }

  function groupStatementsBySection(statements) {
    const groups = [];
    const indexByKey = {};
    (statements || []).forEach(function (stmt) {
      const key =
        stmt.section != null && stmt.section !== ""
          ? String(stmt.section)
          : "__none__";
      if (indexByKey[key] === undefined) {
        indexByKey[key] = groups.length;
        groups.push({
          section: stmt.section,
          section_name: sectionLabel(stmt),
          statements: [],
        });
      }
      groups[indexByKey[key]].statements.push(stmt);
    });
    return groups;
  }

  function sectionGroupKey(group) {
    return group.section != null && group.section !== "" ? String(group.section) : "__none__";
  }

  function sectionReducedWeights(statements) {
    const raw = statements.map(function (s) {
      if (s.reduced_importance_section != null) {
        return Number(s.reduced_importance_section);
      }
      if (s.importance_section != null) {
        return Number(s.importance_section);
      }
      return Number(s.importance || 0);
    });
    const total = raw.reduce(function (sum, w) {
      return sum + w;
    }, 0);
    if (total <= 0) {
      const share = statements.length ? 100 / statements.length : 0;
      return raw.map(function () {
        return share;
      });
    }
    return raw.map(function (w) {
      return (w / total) * 100;
    });
  }

  function computeSectionCsat(statements, useCurrentScores) {
    if (!statements.length) return 0;
    const weights = sectionReducedWeights(statements);
    let total = 0;
    statements.forEach(function (s, i) {
      const perf = useCurrentScores
        ? scores[s.column] != null
          ? Number(scores[s.column])
          : Number(s.performance)
        : Number(s.performance);
      total += perf * weights[i];
    });
    return Math.round(total / 10) / 10;
  }

  function sectionScoresUnchanged(statements) {
    return statements.every(function (s) {
      const col = s.column;
      if (scores[col] == null || originalScores[col] == null) return false;
      return Math.round(Number(scores[col])) === Math.round(Number(originalScores[col]));
    });
  }

  function createSectionGaugePanel(group) {
    const key = sectionGroupKey(group);
    const panel = document.createElement("aside");
    panel.className = "sim-section-gauge-panel";

    const label = document.createElement("p");
    label.className = "sim-section-gauge-label";
    label.textContent = "Section CSAT";

    const gaugeWrap = document.createElement("div");
    gaugeWrap.className = "sim-section-gauge";
    gaugeWrap.setAttribute("role", "meter");
    gaugeWrap.setAttribute("aria-valuemin", "0");
    gaugeWrap.setAttribute("aria-valuemax", "100");
    gaugeWrap.setAttribute("aria-valuenow", "0");
    gaugeWrap.setAttribute("aria-label", group.section_name + " CSAT");

    const dial = document.createElement("div");
    dial.className = "sim-section-gauge-dial";

    const canvas = document.createElement("canvas");
    canvas.className = "sim-section-gauge-canvas";
    canvas.width = SECTION_GAUGE.width;
    canvas.height = SECTION_GAUGE.height;
    canvas.setAttribute("aria-hidden", "true");
    dial.appendChild(canvas);

    const valueEl = document.createElement("div");
    valueEl.className = "sim-section-gauge-value";
    valueEl.textContent = "—";

    const meta = document.createElement("div");
    meta.className = "sim-section-gauge-meta";

    const baselineWrap = document.createElement("span");
    baselineWrap.className = "sim-section-baseline";
    baselineWrap.innerHTML = 'from <span class="sim-section-baseline-value">—</span>';

    const deltaBadge = document.createElement("span");
    deltaBadge.className = "sim-section-delta";
    deltaBadge.hidden = true;
    deltaBadge.innerHTML =
      '<span class="sim-delta-icon" aria-hidden="true">↗</span> <span class="sim-section-delta-text">+0 pts</span>';

    meta.appendChild(baselineWrap);
    meta.appendChild(deltaBadge);

    gaugeWrap.appendChild(dial);
    gaugeWrap.appendChild(valueEl);
    gaugeWrap.appendChild(meta);
    panel.appendChild(label);
    panel.appendChild(gaugeWrap);

    sectionGaugeState[key] = {
      key: key,
      canvas: canvas,
      gaugeEl: gaugeWrap,
      valueEl: valueEl,
      baselineEl: baselineWrap.querySelector(".sim-section-baseline-value"),
      deltaBadge: deltaBadge,
      deltaText: deltaBadge.querySelector(".sim-section-delta-text"),
      gaugeValue: 0,
      baseline: null,
      animFrame: null,
    };

    drawGaugeOnCanvas(canvas, 0, SECTION_GAUGE);
    return panel;
  }

  function isZeroDelta(delta) {
    return delta == null || Math.abs(Number(delta)) < 0.05;
  }

  function clearAllDeltaBadges() {
    if (deltaBadge) {
      deltaBadge.hidden = true;
      deltaBadge.classList.remove("is-negative");
    }
    Object.keys(sectionGaugeState).forEach(function (key) {
      const state = sectionGaugeState[key];
      if (state && state.deltaBadge) {
        state.deltaBadge.hidden = true;
        state.deltaBadge.classList.remove("is-negative");
      }
    });
  }

  function animateSectionGauge(state, displayValue, baseline, delta, options) {
    const opts = options || {};
    const target = Math.max(0, Math.min(100, Number(displayValue) || 0));
    const intro = !!opts.intro && !prefersReducedMotion;
    const from = intro ? 0 : state.gaugeValue;

    if (state.baselineEl) state.baselineEl.textContent = formatPct(baseline);
    if (state.gaugeEl) state.gaugeEl.setAttribute("aria-valuenow", String(Math.round(target)));

    if (state.deltaBadge && state.deltaText) {
      if (isZeroDelta(delta)) {
        state.deltaBadge.hidden = true;
        state.deltaBadge.classList.remove("is-negative");
      } else {
        state.deltaBadge.hidden = false;
        const sign = delta > 0 ? "+" : "";
        state.deltaText.textContent = sign + delta + " pts";
        state.deltaBadge.classList.toggle("is-negative", delta < 0);
        const icon = state.deltaBadge.querySelector(".sim-delta-icon");
        if (icon) icon.textContent = delta >= 0 ? "↗" : "↘";
      }
    }

    if (state.animFrame) cancelAnimationFrame(state.animFrame);

    if (prefersReducedMotion || (!intro && Math.abs(target - from) < 0.25)) {
      state.gaugeValue = target;
      drawGaugeOnCanvas(state.canvas, state.gaugeValue, SECTION_GAUGE);
      if (state.valueEl) state.valueEl.textContent = formatPct(target);
      return;
    }

    const duration = intro ? 1650 : 480;
    const start = performance.now();

    function frame(now) {
      const t = Math.min(1, (now - start) / duration);
      const eased = gaugeEase(t, intro);
      state.gaugeValue = from + (target - from) * eased;
      drawGaugeOnCanvas(state.canvas, state.gaugeValue, SECTION_GAUGE);
      if (state.valueEl) state.valueEl.textContent = formatPct(state.gaugeValue);
      if (t < 1) {
        state.animFrame = requestAnimationFrame(frame);
      } else {
        state.gaugeValue = target;
        state.animFrame = null;
        if (state.valueEl) state.valueEl.textContent = formatPct(target);
      }
    }

    state.animFrame = requestAnimationFrame(frame);
  }

  function updateSectionGauges(options) {
    if (!meta) return;
    const opts = options || {};
    const isIntro = !!opts.intro && !sectionGaugesIntroDone;

    groupStatementsBySection(meta.statements).forEach(function (group) {
      const key = sectionGroupKey(group);
      const state = sectionGaugeState[key];
      if (!state) return;

      const baseline = computeSectionCsat(group.statements, false);
      state.baseline = baseline;
      const unchanged = sectionScoresUnchanged(group.statements);
      const displayValue = unchanged ? baseline : computeSectionCsat(group.statements, true);
      const delta = unchanged ? 0 : Math.round((displayValue - baseline) * 10) / 10;

      animateSectionGauge(state, displayValue, baseline, delta, {
        intro: isIntro && unchanged,
      });
    });

    if (isIntro) sectionGaugesIntroDone = true;
  }

  function createStatementRow(stmt) {
    const col = stmt.column;
    const current = Number(stmt.performance);
    const simulated = scores[col] != null ? Number(scores[col]) : current;

    const row = document.createElement("div");
    row.className = "sim-statement-row";
    row.dataset.column = col;

    const header = document.createElement("div");
    header.className = "sim-statement-header";

    const label = document.createElement("span");
    label.className = "sim-statement-label";
    label.textContent = stmt.label || col;

    const values = document.createElement("span");
    values.className = "sim-statement-values";
    values.innerHTML =
      '<span class="sim-val-current">' +
      formatPct(current) +
      '</span> <span class="sim-val-arrow">→</span> <span class="sim-val-sim">' +
      formatPct(simulated) +
      "</span>";

    header.appendChild(label);
    header.appendChild(values);

    const sliderWrap = document.createElement("div");
    sliderWrap.className = "sim-slider-wrap";

    const slider = document.createElement("input");
    slider.type = "range";
    slider.min = "0";
    slider.max = "100";
    slider.step = "1";
    slider.value = String(Math.round(simulated));
    slider.className = "sim-slider";
    slider.setAttribute("aria-label", "Simulated performance for " + (stmt.label || col));

    function refreshSliderVisual() {
      const val = Math.round(Number(slider.value));
      slider.style.setProperty("--sim-slider-pct", val + "%");
      const changed = val !== Math.round(current);
      row.classList.toggle("is-changed", changed);
      slider.classList.toggle("is-changed", changed);
    }

    slider.addEventListener("input", function () {
      scores[col] = Number(slider.value);
      values.querySelector(".sim-val-sim").textContent = formatPct(slider.value);
      refreshSliderVisual();
      updateSectionGauges();
      schedulePredict();
    });

    slider.addEventListener("pointerdown", function () {
      row.classList.add("is-dragging");
    });
    slider.addEventListener("pointerup", function () {
      row.classList.remove("is-dragging");
    });
    slider.addEventListener("pointercancel", function () {
      row.classList.remove("is-dragging");
    });

    refreshSliderVisual();
    sliderWrap.appendChild(slider);

    row.appendChild(header);
    row.appendChild(sliderWrap);
    return row;
  }

  function renderStatements() {
    if (!meta || !listEl) return;
    listEl.innerHTML = "";
    Object.keys(sectionGaugeState).forEach(function (key) {
      const state = sectionGaugeState[key];
      if (state && state.animFrame) cancelAnimationFrame(state.animFrame);
    });
    Object.keys(sectionGaugeState).forEach(function (key) {
      delete sectionGaugeState[key];
    });
    sectionGaugesIntroDone = false;

    groupStatementsBySection(meta.statements).forEach(function (group) {
      const sectionWrap = document.createElement("div");
      sectionWrap.className = "sim-section-group";

      const sectionHeader = document.createElement("div");
      sectionHeader.className = "sim-section-header";
      sectionHeader.textContent = group.section_name;
      sectionWrap.appendChild(sectionHeader);

      const sectionLayout = document.createElement("div");
      sectionLayout.className = "sim-section-layout";

      const sectionMain = document.createElement("div");
      sectionMain.className = "sim-section-main";

      const sectionBody = document.createElement("div");
      sectionBody.className = "sim-section-statements";

      group.statements.forEach(function (stmt) {
        sectionBody.appendChild(createStatementRow(stmt));
      });

      sectionMain.appendChild(sectionBody);
      sectionLayout.appendChild(sectionMain);
      sectionLayout.appendChild(createSectionGaugePanel(group));
      sectionWrap.appendChild(sectionLayout);
      listEl.appendChild(sectionWrap);
    });
  }

  function updateResult(data) {
    const baseline = data.baseline_overall;
    const unchanged = scoresMatchOriginal();
    const displayValue = unchanged ? baseline : data.predicted_overall;
    const delta = unchanged ? 0 : isZeroDelta(data.delta_pts) ? 0 : data.delta_pts;
    const isIntro = !gaugeIntroDone;

    if (baselineEl) baselineEl.textContent = formatPct(baseline);

    if (isIntro && unchanged) {
      updateGauge(displayValue, { intro: true });
    } else if (isIntro) {
      updateGauge(displayValue, { intro: true });
    } else {
      if (predictedEl) predictedEl.textContent = formatPct(displayValue);
      updateGauge(displayValue);
    }

    if (deltaBadge && deltaText) {
      if (isZeroDelta(delta)) {
        deltaBadge.hidden = true;
        deltaBadge.classList.remove("is-negative");
      } else {
        deltaBadge.hidden = false;
        const sign = delta > 0 ? "+" : "";
        deltaText.textContent = sign + delta + " pts";
        deltaBadge.classList.toggle("is-negative", delta < 0);
        deltaBadge.querySelector(".sim-delta-icon").textContent = delta >= 0 ? "↗" : "↘";
      }
    }

    updateSectionGauges({ intro: isIntro });
  }

  async function runPredict() {
    if (!meta) return;
    const seq = ++predictSeq;
    try {
      const res = await fetch("/api/simulation/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scores: scores }),
      });
      const data = await readJsonResponse(res);
      if (seq !== predictSeq) return;
      if (!data.ok) throw new Error(data.error || "Prediction failed.");
      updateResult(data);
      const changedRows = buildBottomUpChangedRows();
      const buPayload = {
        bottom_up_scores: scores,
        predicted_overall: data.predicted_overall,
        baseline_overall: data.baseline_overall,
        bottom_up_result: {
          baseline_overall: data.baseline_overall,
          predicted_overall: data.predicted_overall,
          delta_pts: data.delta_pts,
          changed_statements: changedRows,
        },
      };
      if (changedRows.length) buPayload.last_view = "bottom-up";
      persistSummaryState(buPayload);
    } catch (err) {
      showError(err.message || String(err));
    }
  }

  function schedulePredict() {
    clearTimeout(predictTimer);
    predictTimer = setTimeout(runPredict, 120);
  }

  function initScores() {
    scores = {};
    originalScores = {};
    (meta.statements || []).forEach(function (s) {
      const perf = Number(s.performance);
      scores[s.column] = perf;
      originalScores[s.column] = perf;
    });
  }

  function readStoredSummaryState() {
    try {
      const raw = sessionStorage.getItem(SUMMARY_STORAGE_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (e) {
      return null;
    }
  }

  /** Reload improved bottom-up scores from the last saved session JSON. */
  function restoreImprovedScoresFromStorage() {
    const stored = readStoredSummaryState();
    const saved = stored && stored.bottom_up_scores;
    if (!saved || !meta) return false;

    let applied = false;
    (meta.statements || []).forEach(function (s) {
      const col = s.column;
      if (saved[col] == null) return;
      const val = Number(saved[col]);
      if (!Number.isFinite(val)) return;
      scores[col] = Math.max(0, Math.min(100, val));
      applied = true;
    });
    return applied;
  }

  function scoresMatchOriginal() {
    return (meta.statements || []).every(function (s) {
      const col = s.column;
      if (scores[col] == null || originalScores[col] == null) return false;
      return Math.round(Number(scores[col])) === Math.round(Number(originalScores[col]));
    });
  }

  function syncSlidersFromScores() {
    if (!listEl) return;
    listEl.querySelectorAll(".sim-statement-row").forEach(function (row) {
      const col = row.dataset.column;
      const slider = row.querySelector(".sim-slider");
      const simVal = row.querySelector(".sim-val-sim");
      const currentVal = row.querySelector(".sim-val-current");
      if (!slider || col == null || scores[col] == null) return;
      const val = Math.round(Number(scores[col]));
      slider.value = String(val);
      if (simVal) simVal.textContent = formatPct(val);
      slider.style.setProperty("--sim-slider-pct", val + "%");
      const baseline = currentVal
        ? Math.round(Number(String(currentVal.textContent).replace("%", "")))
        : val;
      const changed = val !== baseline;
      row.classList.toggle("is-changed", changed);
      slider.classList.toggle("is-changed", changed);
    });
    updateSectionGauges();
  }

  function resetScores() {
    if (!meta) return;
    predictSeq++;
    initScores();
    clearAllDeltaBadges();
    syncSlidersFromScores();

    const baseline =
      meta.baseline_overall != null ? Number(meta.baseline_overall) : null;
    if (baseline != null) {
      if (gaugeAnimFrame) {
        cancelAnimationFrame(gaugeAnimFrame);
        gaugeAnimFrame = null;
      }
      gaugeValue = baseline;
      if (predictedEl) predictedEl.textContent = formatPct(baseline);
      drawGauge(baseline);
      setGaugeAria(baseline);
    }

    schedulePredict();
  }

  function setAllScoresTo100() {
    if (!meta) return;
    (meta.statements || []).forEach(function (s) {
      scores[s.column] = 100;
    });
    syncSlidersFromScores();
    schedulePredict();
  }

  function setBuExportEnabled(enabled) {
    if (!buExportXlsxBtn) return;
    buExportXlsxBtn.disabled = !enabled;
    buExportXlsxBtn.title = enabled ? "" : "Load simulation data first";
  }

  function setTdExportEnabled(enabled) {
    if (!tdExportXlsxBtn) return;
    tdExportXlsxBtn.disabled = !enabled;
    tdExportXlsxBtn.title = enabled ? "" : "Run top-down simulation first";
  }

  async function downloadXlsxResponse(res, fallbackName) {
    const contentType = (res.headers.get("content-type") || "").toLowerCase();
    if (!res.ok || contentType.includes("application/json")) {
      let msg = "Export failed.";
      try {
        const data = await res.json();
        if (data && data.error) msg = data.error;
      } catch (e) {}
      throw new Error(msg);
    }
    const blob = await res.blob();
    const disposition = res.headers.get("content-disposition") || "";
    let downloadName = fallbackName || "simulation.xlsx";
    const match = /filename\*?=(?:UTF-8''|")?([^\";]+)/i.exec(disposition);
    if (match && match[1]) {
      downloadName = decodeURIComponent(match[1].replace(/"/g, "").trim());
    }
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = downloadName;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  async function exportBottomUpXlsx() {
    if (!meta) {
      showError("Load simulation data first, then export.");
      return;
    }
    if (buExportXlsxBtn) {
      buExportXlsxBtn.disabled = true;
      buExportXlsxBtn.textContent = "Exporting…";
    }
    try {
      const res = await fetch("/api/simulation/export-xlsx", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: "bottom-up", scores: scores }),
      });
      await downloadXlsxResponse(res, "simulation_bottom_up.xlsx");
    } catch (err) {
      showError(err.message || String(err));
    } finally {
      if (buExportXlsxBtn) {
        buExportXlsxBtn.textContent = "Export xlsx";
        setBuExportEnabled(!!meta);
      }
    }
  }

  async function exportTopDownXlsx() {
    if (!meta || !tdTargetInput) {
      showError("Load simulation data first, then export.");
      return;
    }
    const target = Number(tdTargetInput.value);
    if (Number.isNaN(target)) {
      showError("Enter a target overall satisfaction before exporting.");
      return;
    }
    if (tdExportXlsxBtn) {
      tdExportXlsxBtn.disabled = true;
      tdExportXlsxBtn.textContent = "Exporting…";
    }
    try {
      const res = await fetch("/api/simulation/export-xlsx", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: "top-down",
          target_overall: target,
          option_index: tdOptionIndex,
          quadrants: getSelectedQuadrants(),
        }),
      });
      await downloadXlsxResponse(res, "simulation_top_down.xlsx");
    } catch (err) {
      showError(err.message || String(err));
    } finally {
      if (tdExportXlsxBtn) {
        tdExportXlsxBtn.textContent = "Export xlsx";
        setTdExportEnabled(tdReady);
      }
    }
  }

  function bindExportActions() {
    if (buExportXlsxBtn) {
      buExportXlsxBtn.addEventListener("click", exportBottomUpXlsx);
    }
    if (tdExportXlsxBtn) {
      tdExportXlsxBtn.addEventListener("click", exportTopDownXlsx);
    }
  }

  function bindSimulationActions() {
    if (resetScoresBtn) {
      resetScoresBtn.addEventListener("click", resetScores);
    }
    if (setAll100Btn) {
      setAll100Btn.addEventListener("click", setAllScoresTo100);
    }
  }

  function applyModeVisibility() {
    const isBottom = simMode === "bottom-up";
    const isTop = simMode === "top-down";

    modeButtons.forEach(function (btn) {
      const active = btn.getAttribute("data-mode") === simMode;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-selected", active ? "true" : "false");
    });

    if (statusLeft) {
      statusLeft.textContent = "Mode: " + simMode;
    }

    if (!meta) {
      if (modeHintBottom) modeHintBottom.hidden = true;
      if (modeHintTop) modeHintTop.hidden = true;
      if (workspaceEl) workspaceEl.hidden = true;
      if (topdownEl) topdownEl.hidden = true;
      setOsatPanelVisible(false);
      return;
    }

    if (modeHintBottom) modeHintBottom.hidden = !isBottom;
    if (modeHintTop) modeHintTop.hidden = !isTop;

    if (isBottom) {
      if (workspaceEl) workspaceEl.hidden = false;
      if (topdownEl) topdownEl.hidden = true;
      setOsatPanelVisible(true);
      if (statusDetail) {
        statusDetail.textContent =
          "You set scores → weighted OSAT" +
          (meta.metric_label ? " · " + meta.metric_label : "");
      }
      if (statusModel) statusModel.textContent = "Reduced importance model";
    } else if (isTop) {
      if (workspaceEl) workspaceEl.hidden = true;
      if (topdownEl) topdownEl.hidden = false;
      setOsatPanelVisible(false);
      if (statusDetail) {
        statusDetail.textContent =
          "You set a target → model finds required scores" +
          (meta.metric_label ? " · " + meta.metric_label : "");
      }
      if (statusModel) statusModel.textContent = "Reduced importance model";
      if (tdTargetInput && meta.baseline_overall != null && !tdReady) {
        const suggested = Math.min(
          100,
          Math.max(0, Math.round(Number(meta.baseline_overall) + 5))
        );
        tdTargetInput.value = String(suggested);
      }
      tdBiplotFollowSolve = false;
      showTdBaselineBiplot();
      scheduleTopDownSolve(true);
    }
  }

  function setMode(mode) {
    if (mode !== "bottom-up" && mode !== "top-down") return;
    if (simMode === mode) return;
    simMode = mode;
    if (mode === "top-down") {
      tdOptionIndex = 0;
      tdReady = false;
    }
    applyModeVisibility();
  }

  function renderInverseScoreList(listEl, rows, footnoteEl, footnoteText, options) {
    if (!listEl) return;
    listEl.innerHTML = "";
    const opts = options || {};
    const changedOnly = !!opts.changedOnly;

    let visibleRows = rows || [];
    if (changedOnly) {
      visibleRows = visibleRows.filter(function (row) {
        return row.changed;
      });
    }

    if (!visibleRows.length) {
      const empty = document.createElement("li");
      empty.className = "sim-td-empty";
      empty.textContent =
        opts.emptyMessage ||
        "No statement scores changed for the selected quadrant(s).";
      listEl.appendChild(empty);
      if (footnoteEl) {
        footnoteEl.textContent = footnoteText || "";
      }
      return;
    }

    const groups = [];
    const indexByKey = {};
    visibleRows.forEach(function (row) {
      const key =
        row.section != null && row.section !== ""
          ? String(row.section)
          : row.section_name || "other";
      if (indexByKey[key] == null) {
        indexByKey[key] = groups.length;
        groups.push({
          section_name: row.section_name || "Other",
          statements: [],
        });
      }
      groups[indexByKey[key]].statements.push(row);
    });

    groups.forEach(function (group) {
      const sectionLi = document.createElement("li");
      sectionLi.className = "sim-td-section";

      const header = document.createElement("div");
      header.className = "sim-td-section-header";
      header.textContent = group.section_name;
      sectionLi.appendChild(header);

      const inner = document.createElement("ul");
      inner.className = "sim-td-section-list";

      group.statements.forEach(function (row) {
        const li = document.createElement("li");
        li.className = "sim-td-row";
        const delta =
          row.delta_pts != null
            ? row.delta_pts
            : Number(row.required_performance) - Number(row.performance);
        const deltaNum = Number(delta);
        const deltaText =
          (deltaNum > 0 ? "+" : "") +
          (Number.isFinite(deltaNum) ? deltaNum.toFixed(1) : "0") +
          " pts";
        const deltaClass =
          "sim-td-delta" +
          (deltaNum < 0 ? " is-down" : deltaNum > 0 ? " is-up" : "");
        li.innerHTML =
          '<span class="sim-td-row-label">' +
          escapeHtml(row.label) +
          '</span><span class="sim-td-row-values">' +
          '<span class="sim-td-from">' +
          escapeHtml(formatPct(row.performance)) +
          '</span><span class="sim-td-arrow">→</span>' +
          '<span class="sim-td-to' +
          (deltaNum < 0 ? " is-down" : "") +
          '">' +
          escapeHtml(formatPct(row.required_performance)) +
          '</span><span class="' +
          deltaClass +
          '">' +
          escapeHtml(deltaText) +
          "</span></span>";
        inner.appendChild(li);
      });

      sectionLi.appendChild(inner);
      listEl.appendChild(sectionLi);
    });

    if (footnoteEl && footnoteText) {
      footnoteEl.textContent = footnoteText;
    }
  }

  function getSelectedQuadrants() {
    const selected = [];
    tdQuadrantInputs.forEach(function (input) {
      if (input.checked) selected.push(input.value);
    });
    return selected;
  }

  function shortTdBiplotLabel(label) {
    const text = String(label || "");
    return text.length > 22 ? text.slice(0, 20).trim() + "…" : text;
  }

  function tdComputeAxisRange(values) {
    const PAD = 0.35;
    let extent = 1.2;
    values.forEach(function (v) {
      const n = Number(v);
      if (!Number.isNaN(n)) {
        extent = Math.max(extent, Math.abs(n) + PAD);
      }
    });
    return { min: -extent, max: extent };
  }

  function tdBiplotShapes(xRange, yRange) {
    return [
      {
        type: "rect",
        xref: "x",
        yref: "y",
        x0: 0,
        x1: xRange.max,
        y0: 0,
        y1: yRange.max,
        fillcolor: TD_QUADRANT_THEME.maintain.fill,
        line: { width: 0 },
        layer: "below",
      },
      {
        type: "rect",
        xref: "x",
        yref: "y",
        x0: xRange.min,
        x1: 0,
        y0: 0,
        y1: yRange.max,
        fillcolor: TD_QUADRANT_THEME.urgent.fill,
        line: { width: 0 },
        layer: "below",
      },
      {
        type: "rect",
        xref: "x",
        yref: "y",
        x0: xRange.min,
        x1: 0,
        y0: yRange.min,
        y1: 0,
        fillcolor: TD_QUADRANT_THEME.low.fill,
        line: { width: 0 },
        layer: "below",
      },
      {
        type: "rect",
        xref: "x",
        yref: "y",
        x0: 0,
        x1: xRange.max,
        y0: yRange.min,
        y1: 0,
        fillcolor: TD_QUADRANT_THEME.overkill.fill,
        line: { width: 0 },
        layer: "below",
      },
      {
        type: "line",
        xref: "x",
        yref: "y",
        x0: xRange.min,
        x1: xRange.max,
        y0: 0,
        y1: 0,
        line: { color: "#c9ced8", width: 1 },
        layer: "below",
      },
      {
        type: "line",
        xref: "x",
        yref: "y",
        x0: 0,
        x1: 0,
        y0: yRange.min,
        y1: yRange.max,
        line: { color: "#c9ced8", width: 1 },
        layer: "below",
      },
    ];
  }

  function tdBiplotAnnotations(xRange, yRange) {
    const xPad = (xRange.max - xRange.min) * 0.04;
    const yPad = (yRange.max - yRange.min) * 0.06;
    return [
      {
        x: xRange.min + xPad,
        y: yRange.max - yPad,
        xref: "x",
        yref: "y",
        text: "Low performance high importance",
        showarrow: false,
        xanchor: "left",
        yanchor: "top",
        font: { size: 10, color: TD_QUADRANT_THEME.urgent.quadrantLabel },
      },
      {
        x: xRange.max - xPad,
        y: yRange.max - yPad,
        xref: "x",
        yref: "y",
        text: "High performance high importance",
        showarrow: false,
        xanchor: "right",
        yanchor: "top",
        font: { size: 10, color: TD_QUADRANT_THEME.maintain.quadrantLabel },
      },
      {
        x: xRange.min + xPad,
        y: yRange.min + yPad,
        xref: "x",
        yref: "y",
        text: "Low performance low importance",
        showarrow: false,
        xanchor: "left",
        yanchor: "bottom",
        font: { size: 10, color: TD_QUADRANT_THEME.low.quadrantLabel },
      },
      {
        x: xRange.max - xPad,
        y: yRange.min + yPad,
        xref: "x",
        yref: "y",
        text: "High performance low importance",
        showarrow: false,
        xanchor: "right",
        yanchor: "bottom",
        font: { size: 10, color: TD_QUADRANT_THEME.overkill.quadrantLabel },
      },
    ];
  }

  function buildTdBiplotTraces(points) {
    const traces = [];

    TD_BIPLOT_ORDER.forEach(function (quadrant) {
      const theme = TD_QUADRANT_THEME[quadrant];
      const pts = points.filter(function (p) {
        return p.quadrant === quadrant;
      });
      if (!pts.length) return;
      traces.push({
        type: "scatter",
        mode: "markers+text",
        x: pts.map(function (p) {
          return Number(p.z_performance);
        }),
        y: pts.map(function (p) {
          return Number(p.z_importance);
        }),
        text: pts.map(function (p) {
          return shortTdBiplotLabel(p.label);
        }),
        textposition: "middle center",
        textfont: {
          size: 10,
          color: "#1b254a",
          family: "Plus Jakarta Sans, system-ui, sans-serif",
        },
        marker: {
          size: pts.map(function (p) {
            return p.changed ? 15 : 12;
          }),
          color: theme.dot,
          line: {
            color: pts.map(function (p) {
              return p.changed ? "#1b254a" : "#ffffff";
            }),
            width: pts.map(function (p) {
              return p.changed ? 2 : 1.5;
            }),
          },
        },
        customdata: pts.map(function (p) {
          return [
            p.required_performance,
            p.importance,
            p.z_performance,
            p.z_importance,
            p.delta_pts,
          ];
        }),
        hovertext: pts.map(function (p) {
          return p.label;
        }),
        hovertemplate:
          "<b>%{hovertext}</b><br>Required: %{customdata[0]}%<br>Importance: %{customdata[1]}%<br>Δ: %{customdata[4]} pts<br>Z perf: %{customdata[2]}<br>Z imp: %{customdata[3]}<extra></extra>",
        name: theme.label,
        showlegend: false,
      });
    });

    return traces;
  }

  const tdBiplotWrap = document.getElementById("sim-td-biplot-wrap");
  let lastTdBiplotHeight = 0;
  let tdBiplotResizeTimer = null;
  let tdBiplotResizing = false;

  function updateTdWorkspaceLayout() {
    lastTdBiplotHeight = 0;
    requestAnimationFrame(function () {
      requestAnimationFrame(scheduleTdBiplotResize);
    });
  }

  function getTdBiplotHeight() {
    if (isTdBiplotFullscreen()) {
      if (tdBiplotWrap) {
        const h = Math.floor(tdBiplotWrap.getBoundingClientRect().height);
        if (h > 120) return h;
      }
      return Math.max(320, window.innerHeight - 140);
    }
    if (tdBiplotWrap) {
      const h = Math.floor(tdBiplotWrap.getBoundingClientRect().height);
      if (h > 120) return h;
    }
    return 720;
  }

  function resizeTdBiplot() {
    if (!tdBiplotEl || !window.Plotly || !tdBiplotEl.data || tdBiplotResizing) return;
    const height = getTdBiplotHeight();
    if (Math.abs(height - lastTdBiplotHeight) < 2) return;

    const scrollRoot = document.querySelector(".main-wrapper");
    const scrollTop = scrollRoot ? scrollRoot.scrollTop : 0;
    tdBiplotResizing = true;
    lastTdBiplotHeight = height;

    window.Plotly.relayout(tdBiplotEl, {
      height: height,
      autosize: true,
    })
      .catch(function () {})
      .then(function () {
        tdBiplotResizing = false;
        if (scrollRoot && Math.abs(scrollRoot.scrollTop - scrollTop) > 1) {
          scrollRoot.scrollTop = scrollTop;
        }
      });
  }

  function scheduleTdBiplotResize() {
    if (tdBiplotResizeTimer) {
      window.clearTimeout(tdBiplotResizeTimer);
    }
    tdBiplotResizeTimer = window.setTimeout(function () {
      tdBiplotResizeTimer = null;
      resizeTdBiplot();
    }, 120);
  }

  function resetTdBiplotView() {
    if (!tdBiplotEl || !window.Plotly || !tdBiplotAxisRange) return;
    window.Plotly.relayout(tdBiplotEl, {
      "xaxis.range": [tdBiplotAxisRange.x.min, tdBiplotAxisRange.x.max],
      "yaxis.range": [tdBiplotAxisRange.y.min, tdBiplotAxisRange.y.max],
      "xaxis.autorange": false,
      "yaxis.autorange": false,
    });
  }

  function isTdBiplotFullscreen() {
    return document.fullscreenElement === tdBiplotCard;
  }

  async function toggleTdBiplotFullscreen() {
    if (!tdBiplotCard) return;
    try {
      if (isTdBiplotFullscreen()) {
        await document.exitFullscreen();
      } else {
        await tdBiplotCard.requestFullscreen();
      }
    } catch (_err) {
      /* fullscreen may be blocked */
    }
  }

  function updateTdBiplotFullscreenButton() {
    if (!tdBiplotFullscreenBtn) return;
    const open = isTdBiplotFullscreen();
    tdBiplotFullscreenBtn.textContent = open ? "Exit fullscreen" : "Fullscreen";
    tdBiplotFullscreenBtn.setAttribute(
      "aria-label",
      open ? "Exit fullscreen chart" : "Fullscreen chart"
    );
    lastTdBiplotHeight = 0;
    scheduleTdBiplotResize();
  }

  function renderTdBiplot(points) {
    if (!tdBiplotEl || !window.Plotly) return;
    if (tdBiplotCard) tdBiplotCard.hidden = false;

    const xVals = [];
    const yVals = [];
    (points || []).forEach(function (p) {
      xVals.push(Number(p.z_performance));
      yVals.push(Number(p.z_importance));
    });
    const xRange = tdComputeAxisRange(xVals);
    const yRange = tdComputeAxisRange(yVals);
    tdBiplotAxisRange = { x: xRange, y: yRange };

    const traces = buildTdBiplotTraces(points || []);
    if (!traces.length) {
      traces.push({
        type: "scatter",
        mode: "markers",
        x: [0],
        y: [0],
        marker: { opacity: 0 },
        hoverinfo: "skip",
        showlegend: false,
      });
    }

    lastTdBiplotHeight = 0;
    const layout = {
      autosize: true,
      height: getTdBiplotHeight(),
      paper_bgcolor: "#ffffff",
      plot_bgcolor: "#ffffff",
      margin: { l: 52, r: 28, t: 28, b: 48 },
      hovermode: "closest",
      dragmode: "zoom",
      xaxis: {
        title: {
          text: "Performance →",
          font: { size: 12, color: "#6b7280", family: "Plus Jakarta Sans, system-ui, sans-serif" },
        },
        range: [xRange.min, xRange.max],
        zeroline: false,
        showgrid: true,
        gridcolor: "rgba(27,37,74,0.08)",
        tickfont: { color: "#6b7280", size: 11 },
        linecolor: "#e6e8ee",
        fixedrange: false,
      },
      yaxis: {
        title: {
          text: "Importance →",
          font: { size: 12, color: "#6b7280", family: "Plus Jakarta Sans, system-ui, sans-serif" },
        },
        range: [yRange.min, yRange.max],
        zeroline: false,
        showgrid: true,
        gridcolor: "rgba(27,37,74,0.08)",
        tickfont: { color: "#6b7280", size: 11 },
        linecolor: "#e6e8ee",
        fixedrange: false,
      },
      shapes: tdBiplotShapes(xRange, yRange),
      annotations: tdBiplotAnnotations(xRange, yRange),
      hoverlabel: {
        bgcolor: "#ffffff",
        bordercolor: "#e6e8ee",
        font: { color: "#12141a", family: "Plus Jakarta Sans, system-ui, sans-serif", size: 13 },
      },
    };

    const plotPromise = tdBiplotEl.data
      ? window.Plotly.react(tdBiplotEl, traces, layout, TD_BIPLOT_CONFIG)
      : window.Plotly.newPlot(tdBiplotEl, traces, layout, TD_BIPLOT_CONFIG);

    plotPromise.then(function () {
      requestAnimationFrame(function () {
        requestAnimationFrame(scheduleTdBiplotResize);
      });
    });
  }

  /** Achieved OSAT always spans every statement, including the locked ones. */
  function renderTdAchieved(data) {
    if (!tdAchievedEl) return;
    const selected = (data && data.quadrants) || [];

    if (!data || !selected.length) {
      tdAchievedEl.hidden = true;
      tdAchievedEl.textContent = "";
      tdAchievedEl.classList.remove("is-short");
      return;
    }

    tdAchievedEl.hidden = false;
    tdAchievedEl.classList.toggle("is-short", data.feasible === false);
    tdAchievedEl.textContent =
      "target " +
      formatPct(data.target_overall) +
      " · achieved " +
      formatPct(data.achieved_overall);
  }

  function showTdBaselineBiplot() {
    if (!meta) return;
    renderTdAchieved(null);
    updateTdWorkspaceLayout();
    renderTdBiplot(meta.biplot || []);
    if (tdResultsEl) tdResultsEl.hidden = false;
    renderInverseScoreList(tdListEl, [], null, null, {
      changedOnly: true,
      emptyMessage:
        "No score changes yet. Select a quadrant to see updated performance scores here.",
    });
  }

  function renderTopDownResults(data) {
    if (!tdResultsEl || !tdListEl) return;
    const option = data.option || {};
    const rows = option.statements || [];
    const selectedQuadrants = data.quadrants || [];

    updateTdWorkspaceLayout();
    tdResultsEl.hidden = false;
    renderTdAchieved(data);

    renderInverseScoreList(tdListEl, rows, null, null, {
      changedOnly: true,
      emptyMessage: !selectedQuadrants.length
        ? "No score changes yet. Select a quadrant to see updated performance scores here."
        : "No statement scores changed for the selected quadrant(s).",
    });

    if (tdBiplotFollowSolve && selectedQuadrants.length) {
      renderTdBiplot(data.biplot || option.biplot || []);
    } else if (meta) {
      renderTdBiplot(meta.biplot || []);
    }
    scheduleTdBiplotResize();
  }

  async function runTopDownSolve() {
    if (tdTargetInput.value < meta.baseline_overall) {
      showError(
        "Target overall satisfaction must be greater than baseline value.",
        true
      );
      return;
    }

    if (!meta || simMode !== "top-down") return;
    if (!tdTargetInput) return;

    const target = Number(tdTargetInput.value);
    if (Number.isNaN(target)) {
      showError("Enter a numeric target overall satisfaction.");
      return;
    }

    const quadrants = getSelectedQuadrants();

    try {
      hideError();
      if (promptEl) promptEl.hidden = true;
      const res = await fetch("/api/simulation/top-down", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_overall: target,
          option_index: tdOptionIndex,
          quadrants: quadrants,
        }),
      });
      const data = await readJsonResponse(res);
      if (!data.ok) throw new Error(data.error || "Top-down solve failed.");
      tdReady = true;
      setTdExportEnabled(true);
      tdOptionIndex = data.option_index || 0;
      renderTopDownResults(data);
      if (statusModel) statusModel.textContent = "Reduced importance model";
      persistSummaryState({
        last_view: "top-down",
        target_overall: target,
        top_down_option_index: tdOptionIndex,
        top_down_quadrants: quadrants,
        top_down_result: {
          baseline_overall: data.baseline_overall,
          target_overall: data.target_overall,
          achieved_overall: data.achieved_overall,
          feasible: data.feasible,
          quadrants: data.quadrants || quadrants,
          eligible_count: data.eligible_count,
          changed_count: data.changed_count,
          changed_statements: buildTopDownChangedRows(data),
        },
      });
    } catch (err) {
      if (tdResultsEl) tdResultsEl.hidden = true;
      if (tdBiplotCard) tdBiplotCard.hidden = true;
      if (errorEl && errorText) {
        errorText.textContent = err.message || String(err);
        errorEl.hidden = false;
      }
    }
  }

  function scheduleTopDownSolve(immediate) {
    if (tdSolveTimer) clearTimeout(tdSolveTimer);
    if (immediate) {
      runTopDownSolve();
      return;
    }
    tdSolveTimer = setTimeout(function () {
      runTopDownSolve();
    }, 280);
  }

  function bindModeAndTopDown() {
    modeButtons.forEach(function (btn) {
      if (btn.disabled) return;
      btn.addEventListener("click", function () {
        setMode(btn.getAttribute("data-mode"));
      });
    });

    if (tdTargetInput) {
      tdTargetInput.addEventListener("input", function () {
        tdOptionIndex = 0;
        tdBiplotFollowSolve = getSelectedQuadrants().length > 0;
        scheduleTopDownSolve(false);
      });
      tdTargetInput.addEventListener("change", function () {
        tdOptionIndex = 0;
        tdBiplotFollowSolve = getSelectedQuadrants().length > 0;
        scheduleTopDownSolve(true);
      });
    }

    tdQuadrantInputs.forEach(function (input) {
      input.addEventListener("change", function () {
        tdOptionIndex = 0;
        const selected = getSelectedQuadrants();
        tdBiplotFollowSolve = selected.length > 0;
        updateTdWorkspaceLayout();
        if (!selected.length) {
          showTdBaselineBiplot();
        }
        scheduleTopDownSolve(true);
      });
    });

    if (tdBiplotResetBtn) {
      tdBiplotResetBtn.addEventListener("click", resetTdBiplotView);
    }
    if (tdBiplotFullscreenBtn) {
      tdBiplotFullscreenBtn.addEventListener("click", toggleTdBiplotFullscreen);
    }
    document.addEventListener("fullscreenchange", updateTdBiplotFullscreenButton);
    window.addEventListener("resize", scheduleTdBiplotResize);

    if (typeof ResizeObserver !== "undefined" && tdBiplotCard) {
      const tdRo = new ResizeObserver(function () {
        if (tdBiplotResizing) return;
        lastTdBiplotHeight = 0;
        scheduleTdBiplotResize();
      });
      tdRo.observe(tdBiplotCard);
    }
  }

  bindSimulationActions();
  bindExportActions();
  bindModeAndTopDown();
  if (modeHintBottom) modeHintBottom.hidden = true;
  if (modeHintTop) modeHintTop.hidden = true;
  setOsatPanelVisible(false);

  async function loadMeta() {
    try {
      const hasUpload = window.gapAnalyzerSessionReady
        ? await window.gapAnalyzerSessionReady
        : false;
      if (!hasUpload) {
        showPrompt(
          'Upload a survey file first on the <a href="/upload">Upload</a> page ' +
            "before running a simulation."
        );
        return;
      }

      const res = await fetch("/api/simulation/meta");
      const data = await res.json();
      if (!data.ok) {
        if (data.needs_gap_analysis) {
          showPrompt(
            'Run <a href="/gap-analysis">gap analysis</a> first (choose scale and metric) ' +
              "to load statement performance scores."
          );
          return;
        }
        if (/no upload/i.test(data.error || "")) {
          showPrompt(
            'Upload a survey file first on the <a href="/upload">Upload</a> page ' +
              "before running a simulation."
          );
          return;
        }
        throw new Error(data.error || "Could not load simulation data.");
      }

      meta = data;
      hideError();
      if (promptEl) promptEl.hidden = true;
      setBuExportEnabled(true);

      initScores();
      restoreImprovedScoresFromStorage();
      if (baselineEl && data.baseline_overall != null) {
        baselineEl.textContent = formatPct(data.baseline_overall);
      }

      if (statusModel && data.model) {
        if (data.model.train_r2 != null) {
          statusModel.textContent =
            "Reduced importance · MLR train R² " +
            Number(data.model.train_r2).toFixed(2);
        } else {
          statusModel.textContent = "Reduced importance model";
        }
      }

      renderStatements();
      applyModeVisibility();
      if (simMode === "bottom-up") {
        await runPredict();
      }
    } catch (err) {
      showError(err.message || String(err));
    }
  }

  loadMeta();
})();
