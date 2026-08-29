/**
 * Gap analysis — MLR importance + performance bi-plot.
 * Results appear only after scale and metric are chosen.
 */

(function () {
  const STORAGE_KEY = "gapAnalyzer_gap_session";
  const META_KEY = "gapAnalyzer_gap_meta";
  const SIM_SNAPSHOT_KEY = "gapAnalyzer_sim_snapshot";
  const SIM_META_KEY = "gapAnalyzer_sim_meta";

  const scaleSelect = document.getElementById("gap-scale");
  const metricSelect = document.getElementById("gap-metric");
  const sectionSelect = document.getElementById("gap-section");
  const promptEl = document.getElementById("gap-prompt");
  const loadingEl = document.getElementById("gap-loading");
  const errorEl = document.getElementById("gap-error");
  const errorText = document.getElementById("gap-error-text");
  const resultsEl = document.getElementById("gap-results");
  const modelSpinner = document.getElementById("gap-model-spinner");
  const modelStatusText = document.getElementById("gap-model-status-text");
  const modelQualityBtn = document.getElementById("gap-model-quality-btn");
  const modelQualityPanel = document.getElementById("gap-model-quality-panel");
  const modelQualityHint = document.getElementById("gap-model-quality-hint");
  const modelQualityMetrics = document.getElementById("gap-model-quality-metrics");
  const fitProgressEl = document.getElementById("gap-fit-progress");
  const biplotEl = document.getElementById("gap-biplot");
  const biplotWrap = document.getElementById("gap-biplot-wrap");
  const biplotCard = document.getElementById("gap-biplot-card");
  const biplotControls = document.getElementById("gap-biplot-controls");
  const biplotHint = document.getElementById("gap-biplot-hint");
  const biplotResetBtn = document.getElementById("gap-biplot-reset");
  const biplotFullscreenBtn = document.getElementById("gap-biplot-fullscreen");
  const priorityList = document.getElementById("priority-list");
  const priorityCount = document.getElementById("priority-count");
  const tableBody = document.getElementById("gap-table-body");
  const statusLeft = document.getElementById("gap-status-left");
  const statusMetric = document.getElementById("gap-status-metric");
  const statusTime = document.getElementById("gap-status-time");
  const exportXlsxBtn = document.getElementById("gap-export-xlsx");

  if (!scaleSelect || !metricSelect) return;

  let meta = null;
  let computeTimer = null;
  let fullResults = null;

  const QUADRANT_THEME = {
    maintain: {
      fill: "rgba(217, 234, 211, 0.85)",
      dot: "#38761d",
      bg: "#d9ead3",
      text: "#38761d",
      quadrantLabel: "#2d5a1a",
      label: "High Performance High Importance",
    },
    low: {
      fill: "rgba(255, 242, 204, 0.9)",
      dot: "#bf9000",
      bg: "#fff2cc",
      text: "#bf9000",
      quadrantLabel: "#8a6800",
      label: "Low Performance Low Importance",
    },
    urgent: {
      fill: "rgba(244, 204, 204, 0.9)",
      dot: "#990000",
      bg: "#f4cccc",
      text: "#990000",
      quadrantLabel: "#7a1010",
      label: "Low Performance High Importance",
    },
    overkill: {
      fill: "rgba(207, 226, 243, 0.9)",
      dot: "#1155cc",
      bg: "#cfe2f3",
      text: "#1155cc",
      quadrantLabel: "#0d3f96",
      label: "High Performance Low Importance",
    },
  };

  function quadrantTheme(quadrant) {
    return QUADRANT_THEME[quadrant] || QUADRANT_THEME.low;
  }

  const BIPLOT_HEIGHT = 480;

  let biplotAxisRange = null;

  const BIPLOT_QUADRANT_ORDER = ["urgent", "maintain", "low", "overkill"];

  const BIPLOT_CONFIG = {
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    scrollZoom: true,
    modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"],
    toImageButtonOptions: {
      format: "png",
      filename: "gap-importance-performance-biplot",
      scale: 2,
    },
  };

  function shortBiplotLabel(label) {
    return label.length > 22 ? label.slice(0, 20).trim() + "…" : label;
  }

  let lastBiplotHeight = 0;
  let biplotResizeTimer = null;
  let biplotResizing = false;

  function getBiplotHeight() {
    const wrap = biplotWrap || (biplotEl && biplotEl.parentElement);
    if (wrap) {
      const h = Math.floor(wrap.getBoundingClientRect().height);
      if (h > 120) return h;
    }
    if (isBiplotFullscreen()) {
      return Math.max(320, window.innerHeight - 140);
    }
    return BIPLOT_HEIGHT;
  }

  function getGapScrollRoot() {
    return document.querySelector(".main-wrapper");
  }

  function resizeBiplot() {
    if (!biplotEl || !window.Plotly || !biplotEl.data || biplotResizing) return;
    const height = getBiplotHeight();
    if (Math.abs(height - lastBiplotHeight) < 2) return;

    const scrollRoot = getGapScrollRoot();
    const scrollTop = scrollRoot ? scrollRoot.scrollTop : 0;
    biplotResizing = true;
    lastBiplotHeight = height;

    window.Plotly.relayout(biplotEl, {
      height: height,
      autosize: true,
    })
      .catch(function () {})
      .then(function () {
        biplotResizing = false;
        if (scrollRoot && Math.abs(scrollRoot.scrollTop - scrollTop) > 1) {
          scrollRoot.scrollTop = scrollTop;
        }
      });
  }

  function scheduleBiplotResize() {
    if (biplotResizeTimer) {
      window.clearTimeout(biplotResizeTimer);
    }
    biplotResizeTimer = window.setTimeout(function () {
      biplotResizeTimer = null;
      resizeBiplot();
    }, 120);
  }

  function resetBiplotView() {
    if (!biplotEl || !window.Plotly || !biplotAxisRange) return;
    window.Plotly.relayout(biplotEl, {
      "xaxis.range": [biplotAxisRange.x.min, biplotAxisRange.x.max],
      "yaxis.range": [biplotAxisRange.y.min, biplotAxisRange.y.max],
      "xaxis.autorange": false,
      "yaxis.autorange": false,
    });
  }

  function showBiplotControls() {
    if (biplotControls) biplotControls.hidden = false;
    if (biplotHint) biplotHint.hidden = false;
  }

  function hideBiplotControls() {
    if (biplotControls) biplotControls.hidden = true;
    if (biplotHint) biplotHint.hidden = true;
    exitBiplotFullscreen();
    purgeBiplot();
  }

  function purgeBiplot() {
    if (biplotEl && window.Plotly) {
      window.Plotly.purge(biplotEl);
    }
    biplotAxisRange = null;
    lastBiplotHeight = 0;
  }

  function isBiplotFullscreen() {
    return document.fullscreenElement === biplotCard;
  }

  async function toggleBiplotFullscreen() {
    if (!biplotCard) return;
    try {
      if (isBiplotFullscreen()) {
        await document.exitFullscreen();
      } else {
        await biplotCard.requestFullscreen();
      }
    } catch (_err) {
      /* fullscreen may be blocked */
    }
  }

  function exitBiplotFullscreen() {
    if (isBiplotFullscreen()) {
      document.exitFullscreen().catch(function () {});
    }
  }

  function updateBiplotFullscreenButton() {
    if (!biplotFullscreenBtn) return;
    const open = isBiplotFullscreen();
    biplotFullscreenBtn.textContent = open ? "Exit fullscreen" : "Fullscreen";
    biplotFullscreenBtn.setAttribute(
      "aria-label",
      open ? "Exit fullscreen chart" : "Fullscreen chart"
    );
    // Wait a frame so fullscreen layout/CSS has applied before measuring.
    lastBiplotHeight = 0;
    scheduleBiplotResize();
  }

  function buildBiplotShapes(xRange, yRange) {
    return [
      {
        type: "rect",
        xref: "x",
        yref: "y",
        x0: 0,
        x1: xRange.max,
        y0: 0,
        y1: yRange.max,
        fillcolor: QUADRANT_THEME.maintain.fill,
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
        fillcolor: QUADRANT_THEME.urgent.fill,
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
        fillcolor: QUADRANT_THEME.low.fill,
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
        fillcolor: QUADRANT_THEME.overkill.fill,
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

  function buildBiplotAnnotations(xRange, yRange) {
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
        font: { size: 10, color: QUADRANT_THEME.urgent.quadrantLabel },
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
        font: { size: 10, color: QUADRANT_THEME.maintain.quadrantLabel },
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
        font: { size: 10, color: QUADRANT_THEME.low.quadrantLabel },
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
        font: { size: 10, color: QUADRANT_THEME.overkill.quadrantLabel },
      },
    ];
  }

  function buildBiplotTraces(points) {
    return BIPLOT_QUADRANT_ORDER.map(function (quadrant) {
      const theme = quadrantTheme(quadrant);
      const pts = points.filter(function (p) {
        return p.quadrant === quadrant;
      });
      if (!pts.length) return null;

      return {
        type: "scatter",
        mode: "markers+text",
        x: pts.map(function (p) {
          return Number(p.z_performance);
        }),
        y: pts.map(function (p) {
          return Number(p.z_importance);
        }),
        text: pts.map(function (p) {
          return shortBiplotLabel(p.label);
        }),
        textposition: "middle center",
        textfont: {
          size: 10,
          color: "#1b254a",
          family: "Plus Jakarta Sans, system-ui, sans-serif",
        },
        marker: {
          size: 13,
          color: theme.dot,
          line: { color: "#ffffff", width: 1.5 },
        },
        customdata: pts.map(function (p) {
          return [p.performance, p.importance, p.z_performance, p.z_importance];
        }),
        hovertext: pts.map(function (p) {
          return p.label;
        }),
        hovertemplate:
          "<b>%{hovertext}</b><br>Performance: %{customdata[0]}%<br>Importance: %{customdata[1]}%<br>Z performance: %{customdata[2]}<br>Z importance: %{customdata[3]}<extra></extra>",
        name: theme.label,
        showlegend: false,
      };
    }).filter(Boolean);
  }

  function bindBiplotControls() {
    if (biplotResetBtn) {
      biplotResetBtn.addEventListener("click", resetBiplotView);
    }
    if (biplotFullscreenBtn) {
      biplotFullscreenBtn.addEventListener("click", toggleBiplotFullscreen);
    }

    document.addEventListener("fullscreenchange", updateBiplotFullscreenButton);
    window.addEventListener("resize", scheduleBiplotResize);

    if (typeof ResizeObserver !== "undefined" && biplotCard) {
      const ro = new ResizeObserver(function () {
        if (biplotResizing) return;
        scheduleBiplotResize();
      });
      ro.observe(biplotCard);
    }
  }

  bindBiplotControls();

  function formatR2(val) {
    if (val == null || val === "") return "—";
    const n = Number(val);
    if (Number.isNaN(n)) return "—";
    return n.toFixed(3);
  }

  function formatVariancePct(val) {
    if (val == null || val === "") return "—";
    const n = Number(val);
    if (Number.isNaN(n)) return "—";
    return (n * 100).toFixed(1) + "%";
  }

  function setModelBarLoading() {
    if (!loadingEl) return;
    loadingEl.hidden = false;
    if (modelSpinner) modelSpinner.hidden = false;
    if (modelStatusText) {
      modelStatusText.textContent = "Training model on uploaded data…";
    }
    if (modelQualityBtn) {
      modelQualityBtn.disabled = true;
      modelQualityBtn.textContent = "Model quality";
      modelQualityBtn.setAttribute("aria-expanded", "false");
      modelQualityBtn.classList.remove("is-open");
    }
    if (modelQualityPanel) modelQualityPanel.hidden = true;
    if (loadingEl) loadingEl.classList.remove("is-quality-open");
  }

  function r2ToneClass(val) {
    if (val == null || val === "") return "";
    const n = Number(val);
    if (Number.isNaN(n)) return "";
    if (n >= 0.7) return "model-r2-good";
    if (n >= 0.3) return "model-r2-moderate";
    return "model-r2-weak";
  }

  function rmseToneClass(val, threshold) {
    if (val == null || val === "" || threshold == null) return "";
    const n = Number(val);
    const t = Number(threshold);
    if (Number.isNaN(n) || Number.isNaN(t)) return "";
    if (n <= t) return "model-rmse-good";
    if (n > t) return "model-rmse-weak";
    return "";
  }

  function formatR2Cell(val, withExplained) {
    const text = formatR2(val);
    if (text === "—") return text;
    const explained = withExplained
      ? " (" + formatVariancePct(val) + " explained)"
      : "";
    const tone = r2ToneClass(val);
    return (
      '<span class="model-r2-value' +
      (tone ? " " + tone : "") +
      '">' +
      escapeHtml(text + explained) +
      "</span>"
    );
  }

  function formatRmseCell(val, threshold, suffix) {
    const text = formatNumber(val, suffix);
    if (text === "—") return text;
    const tone = rmseToneClass(val, threshold);
    return (
      '<span class="model-rmse-value' +
      (tone ? " " + tone : "") +
      '">' +
      escapeHtml(text) +
      "</span>"
    );
  }

  function formatNumber(val, suffix) {
    if (val == null || val === "") return "—";
    const n = Number(val);
    if (Number.isNaN(n)) return "—";
    return String(val) + (suffix || "");
  }

  function isModelMetricsComplete(model) {
    return !!(
      model &&
      model.model_version >= 6 &&
      model.train_r2 != null &&
      model.test_rmse_threshold != null &&
      model.intercept != null
    );
  }

  function headlineR2(model) {
    if (!model) return null;
    return model.train_r2;
  }

  function renderModelQualityMetrics(model) {
    if (!modelQualityMetrics || !model) return;

    const staleNote = !isModelMetricsComplete(model)
      ? '<p class="gap-model-quality-stale">Re-select scale &amp; metric to refresh all model metrics.</p>'
      : "";

    const rmseSuffix = " pts on OSAT scale";
    const rmseThreshold = model.test_rmse_threshold;

    const rows = [
      {
        label: "Train R²",
        html: formatR2Cell(model.train_r2, true),
      },
      {
        label: "Validation RMSE",
        html: formatRmseCell(model.val_rmse, rmseThreshold, rmseSuffix),
      },
      {
        label: "Train RMSE",
        html: formatRmseCell(model.train_rmse, rmseThreshold, rmseSuffix),
      },
      {
        label: "RMSE threshold",
        html:
          escapeHtml("≤ " + formatNumber(rmseThreshold) + " pts (green)") +
          " · scale-aware (25% of OSAT range)",
      },
      {
        label: "Intercept",
        html: escapeHtml(formatNumber(model.intercept)),
      },
      {
        label: "Respondents",
        html: escapeHtml(formatNumber(model.n_respondents)),
      },
      {
        label: "Predictors",
        html: escapeHtml(formatNumber(model.n_predictors)),
      },
      {
        label: "Data split",
        html: escapeHtml(model.split_label || "70% train · 20% validation · 10% test"),
      },
      {
        label: "Sample sizes (train / val / test)",
        html: escapeHtml(
          [model.n_train, model.n_val, model.n_test]
            .map(function (n) {
              return n != null ? String(n) : "—";
            })
            .join(" / ")
        ),
      },
    ];

    modelQualityMetrics.innerHTML =
      staleNote +
      rows
        .map(function (row) {
          return (
            "<div><dt>" +
            escapeHtml(row.label) +
            "</dt><dd>" +
            row.html +
            "</dd></div>"
          );
        })
        .join("");
    if (modelQualityHint) {
      modelQualityHint.textContent = model.quality_hint || "";
    }
  }

  function setModelBarReady(model) {
    if (!loadingEl || !model) return;
    loadingEl.hidden = false;
    if (modelSpinner) modelSpinner.hidden = true;
    const r2 = headlineR2(model);
    const headlineTone = r2ToneClass(r2);
    if (modelStatusText) {
      modelStatusText.innerHTML =
        "✓ MLR model trained · train R² " +
        '<span class="model-r2-value' +
        (headlineTone ? " " + headlineTone : "") +
        '">' +
        escapeHtml(formatR2(r2)) +
        "</span>";
    }
    if (modelQualityBtn) {
      modelQualityBtn.disabled = false;
      modelQualityBtn.innerHTML =
        "Model quality · R² " +
        '<span class="model-r2-value' +
        (headlineTone ? " " + headlineTone : "") +
        '">' +
        escapeHtml(formatR2(r2)) +
        "</span>";
    }
    renderModelQualityMetrics(model);
  }

  function formatFitError(val) {
    if (val == null || val === "") return "—";
    const n = Number(val);
    if (Number.isNaN(n)) return "—";
    if (n >= 10) return n.toFixed(2);
    if (n >= 1) return n.toFixed(3);
    return n.toFixed(4);
  }

  function pickFitCheckpoints(history) {
    if (!history || !history.length) return [];
    if (history.length === 1) return [history[0]];
    if (history.length === 2) return [history[0], history[history.length - 1]];
    const mid = history[Math.floor((history.length - 1) / 2)];
    const last = history[history.length - 1];
    const first = history[0];
    const points = [first];
    if (mid.iteration !== first.iteration && mid.iteration !== last.iteration) {
      points.push(mid);
    }
    points.push(last);
    return points;
  }

  function clearConvergence() {
    if (!fitProgressEl) return;
    fitProgressEl.hidden = true;
    fitProgressEl.innerHTML = "";
  }

  function renderConvergence(model) {
    if (!fitProgressEl) return;
    const gd = model && model.gd;
    const history = gd && Array.isArray(gd.history) ? gd.history : [];
    if (!gd || !history.length) {
      clearConvergence();
      return;
    }

    const points = pickFitCheckpoints(history);
    const trail = points
      .map(function (p, idx) {
        const label =
          idx === 0
            ? "Start"
            : idx === points.length - 1
              ? "Final"
              : "Step " + p.iteration;
        return (
          '<span class="gap-fit-step">' +
          '<span class="gap-fit-step-label">' +
          escapeHtml(label) +
          "</span> " +
          '<span class="gap-fit-step-value">' +
          escapeHtml(formatFitError(p.loss)) +
          "</span></span>"
        );
      })
      .join('<span class="gap-fit-arrow" aria-hidden="true">→</span>');

    const status = model.converged
      ? "Fitting settled after " + gd.iterations + " steps"
      : "Stopped after " + gd.iterations + " steps (limit " + gd.max_iter + ")";

    fitProgressEl.hidden = false;
    fitProgressEl.innerHTML =
      '<span class="gap-fit-progress-label">Prediction error</span> ' +
      '<span class="gap-fit-trail">' +
      trail +
      "</span>" +
      '<span class="gap-fit-progress-status' +
      (model.converged ? " is-settled" : "") +
      '">' +
      escapeHtml(status) +
      "</span>";
  }

  function resetModelBar() {
    if (loadingEl) loadingEl.hidden = true;
    if (modelQualityPanel) modelQualityPanel.hidden = true;
    if (loadingEl) loadingEl.classList.remove("is-quality-open");
    if (modelQualityBtn) {
      modelQualityBtn.disabled = true;
      modelQualityBtn.textContent = "Model quality";
      modelQualityBtn.setAttribute("aria-expanded", "false");
      modelQualityBtn.classList.remove("is-open");
    }
    if (modelStatusText) {
      modelStatusText.textContent = "";
    }
    clearConvergence();
  }

  function toggleModelQualityPanel() {
    if (!modelQualityPanel || !modelQualityBtn || modelQualityBtn.disabled) return;
    const open = modelQualityPanel.hidden;
    modelQualityPanel.hidden = !open;
    modelQualityBtn.setAttribute("aria-expanded", open ? "true" : "false");
    modelQualityBtn.classList.toggle("is-open", open);
    if (loadingEl) loadingEl.classList.toggle("is-quality-open", open);
  }

  function hasSingularBlock() {
    return !!(meta && meta.analysis_blocked);
  }

  function applySingularBlock() {
    const msg =
      (meta && meta.analysis_block_reason) ||
      "Gap analysis is blocked due to collinear statements. Fix them on the Upload page and re-upload.";
    showError(msg);
    scaleSelect.disabled = true;
    metricSelect.disabled = true;
    sectionSelect.disabled = true;
    if (statusLeft) {
      statusLeft.textContent = "Analysis blocked — fix collinear statements on Upload";
    }
    clearGapSession();
  }

  async function ensureServerUpload() {
    if (!window.gapAnalyzerUploadCache) return true;
    try {
      return await window.gapAnalyzerUploadCache.ensureServerUpload();
    } catch (e) {
      return false;
    }
  }

  async function loadMeta() {
    var restored = await ensureServerUpload();
    if (!restored && !sessionStorage.getItem(META_KEY)) {
      throw new Error("No upload data. Please upload a file first.");
    }
    try {
      const res = await fetch("/api/gap-analysis/meta");
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "Could not load upload metadata.");
      meta = data;
      try {
        sessionStorage.setItem(META_KEY, JSON.stringify(data));
      } catch (e) {}
    } catch (err) {
      try {
        const cached = sessionStorage.getItem(META_KEY);
        if (cached) {
          meta = JSON.parse(cached);
        } else {
          throw err;
        }
      } catch (e) {
        throw err;
      }
    }
    if (hasSingularBlock()) {
      populateScales(meta.scales || []);
      populateSections(meta.sections || []);
      applySingularBlock();
      return;
    }
    populateScales(meta.scales || []);
    if (meta.detected_scale) {
      scaleSelect.value = meta.detected_scale;
      updateMetricOptions();
    }
    populateSections(meta.sections || []);
    sectionSelect.disabled = false;
  }

  function saveSimulationBridge(data) {
    if (!data) return;
    try {
      if (data.simulation_snapshot) {
        sessionStorage.setItem(
          SIM_SNAPSHOT_KEY,
          JSON.stringify(data.simulation_snapshot)
        );
      }
      if (data.simulation_meta) {
        sessionStorage.setItem(SIM_META_KEY, JSON.stringify(data.simulation_meta));
      }
    } catch (e) {}
  }

  function populateScales(scales) {
    scaleSelect.innerHTML = '<option value="">Choose scale…</option>';
    scales.forEach(function (s) {
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = s.label;
      scaleSelect.appendChild(opt);
    });
  }

  function populateSections(sections) {
    const prev = sectionSelect.value || "all";
    sectionSelect.innerHTML = '<option value="all">All sections</option>';
    sections.forEach(function (s) {
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = s.name + " (" + s.count + ")";
      sectionSelect.appendChild(opt);
    });
    sectionSelect.value = prev === "all" || !prev ? "all" : prev;
  }

  function updateMetricOptions() {
    const scale = scaleSelect.value;
    metricSelect.innerHTML = '<option value="">Choose metric…</option>';
    metricSelect.disabled = !scale;

    if (!scale || !meta || !meta.metrics_by_scale) return;

    const metrics = meta.metrics_by_scale[scale] || [];
    const seen = {};
    metrics.forEach(function (m) {
      const id = normalizeMetricId(m.id);
      if (seen[id]) return;
      seen[id] = true;
      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = metricDisplayLabel(id, m.label);
      metricSelect.appendChild(opt);
    });
    metricSelect.disabled = metrics.length === 0;
  }

  function getSelections() {
    return {
      scale: scaleSelect.value,
      metric: metricSelect.value,
      section: sectionSelect.value || "all",
    };
  }

  function saveGapSession(results) {
    if (!meta || !results) return;
    try {
      sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          sessionId: meta.session_id || "",
          dataRevision: meta.data_revision || "",
          filename: meta.filename || "",
          selections: getSelections(),
          results: results,
          computedAt: Date.now(),
        })
      );
    } catch (e) {}
  }

  function persistFullResults(data) {
    fullResults = data;
    saveGapSession(data);
  }

  function clearGapSession() {
    sessionStorage.removeItem(STORAGE_KEY);
  }

  function loadGapSession() {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      return raw ? migrateGapCache(JSON.parse(raw)) : null;
    } catch (e) {
      return null;
    }
  }

  function formatComputedTime(ts) {
    const diff = Date.now() - ts;
    if (diff < 60000) return "just now";
    if (diff < 3600000) return Math.floor(diff / 60000) + " min ago";
    return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  const METRIC_LABELS = {
    top2: "Top-2-box",
    top3: "Top-3-box",
    mean: "mean",
  };

  function normalizeMetricId(metric) {
    return metric === "weighted" ? "mean" : metric || "";
  }

  function metricDisplayLabel(metricId, fallback) {
    const id = normalizeMetricId(metricId);
    if (METRIC_LABELS[id]) return METRIC_LABELS[id];
    if (fallback && /weighted|simple mean/i.test(String(fallback))) return METRIC_LABELS.mean;
    return fallback || id;
  }

  function migrateGapCache(cached) {
    if (!cached) return cached;
    if (cached.selections && cached.selections.metric) {
      cached.selections.metric = normalizeMetricId(cached.selections.metric);
    }
    if (cached.results) {
      cached.results.metric_label = metricDisplayLabel(
        cached.selections && cached.selections.metric,
        cached.results.metric_label
      );
      if (
        cached.results.model &&
        !isModelMetricsComplete(cached.results.model)
      ) {
        cached.results = null;
      }
    }
    return cached;
  }

  function selectionsMatch(a, b) {
    return (
      a &&
      b &&
      a.scale === b.scale &&
      normalizeMetricId(a.metric) === normalizeMetricId(b.metric)
    );
  }

  function csatImportanceKey(sectionId) {
    return sectionId === "all" ? "importance" : "importance_section";
  }

  function statementWeight(stmt, importanceKey, sectionStatements) {
    if (importanceKey === "importance_section") {
      if (stmt.importance_section != null) return stmt.importance_section;
      if (!sectionStatements || !sectionStatements.length) return stmt.importance;
      const total = sectionStatements.reduce(function (t, s) {
        return t + s.importance;
      }, 0);
      if (!total) return stmt.importance;
      return Math.round((stmt.importance / total) * 1000) / 10;
    }
    return stmt.importance;
  }

  function sumproductCsat(statements, importanceKey) {
    if (!statements || !statements.length) return 0;
    const key = importanceKey || "importance";
    let weighted = 0;
    let totalImp = 0;
    statements.forEach(function (s) {
      const w = statementWeight(s, key, statements);
      weighted += s.performance * w;
      totalImp += w;
    });
    if (!totalImp) return 0;
    return Math.round((weighted / totalImp) * 10) / 10;
  }

  function getAllStatements(data) {
    if (data.statements && data.statements.length) return data.statements;
    const out = [];
    (data.biplot || []).forEach(function (p) {
      out.push({
        column: p.column,
        section: p.section,
        section_name: p.section_name,
        label: p.label,
        performance: p.performance,
        importance: p.importance,
        quadrant: p.quadrant,
        z_importance: p.z_importance,
        z_performance: p.z_performance,
      });
    });
    return out;
  }

  function filterResultsBySection(data, sectionId) {
    const all = getAllStatements(data);
    const summaryAll = data.summary_all || data.summary || {};
    const catalog = data.sections_catalog || meta.sections || [];

    const filtered =
      sectionId === "all"
        ? all
        : all.filter(function (s) {
            return String(s.section) === String(sectionId);
          });

    const urgent = filtered
      .filter(function (s) {
        return s.quadrant === "urgent";
      })
      .sort(function (a, b) {
        return Number(a.performance) - Number(b.performance);
      });

    const impKey = csatImportanceKey(sectionId);
    const overallCsat = sumproductCsat(filtered, impKey);

    const seen = {};
    filtered.forEach(function (s) {
      if (!seen[s.section]) {
        seen[s.section] = { section: s.section, section_name: s.section_name, statements: [] };
      }
      seen[s.section].statements.push({
        column: s.column,
        label: s.label,
        performance: s.performance,
        importance: s.importance,
        importance_section: s.importance_section,
        quadrant: s.quadrant,
        z_importance: s.z_importance,
        z_performance: s.z_performance,
      });
    });

    const tableSections = Object.keys(seen)
      .sort(function (a, b) {
        return Number(a) - Number(b);
      })
      .map(function (key) {
        return seen[key];
      });

    return {
      summary: {
        sections: sectionId === "all" ? summaryAll.sections || catalog.length : 1,
        statements: filtered.length,
        overall_performance: overallCsat,
        overall_csat: overallCsat,
        fix_urgently: urgent.length,
        respondents: summaryAll.respondents,
      },
      biplot: filtered.map(function (s) {
        return {
          column: s.column,
          label: s.label,
          section: s.section,
          section_name: s.section_name,
          z_importance: s.z_importance,
          z_performance: s.z_performance,
          performance: s.performance,
          importance: s.importance,
          quadrant: s.quadrant,
        };
      }),
      priority_actions: urgent.map(function (s) {
        return {
          label: s.label,
          subtitle: "high importance · " + Math.round(s.performance) + "% satisfied",
        };
      }),
      table: {
        overall_csat: overallCsat,
        overall_performance: overallCsat,
        csat_importance_key: impKey,
        sections: tableSections,
      },
      model: data.model,
      metric_label: metricDisplayLabel(metricSelect.value, data.metric_label),
    };
  }

  function applySectionView() {
    if (!fullResults) return;
    if (!sectionSelect.value) sectionSelect.value = "all";
    const view = filterResultsBySection(fullResults, sectionSelect.value);
    renderResults(view);
    syncGapSessionSelections();
  }

  function syncGapSessionSelections() {
    if (!fullResults) return;
    try {
      const cached = loadGapSession();
      if (!cached || !cached.results) return;
      cached.selections = getSelections();
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(cached));
    } catch (e) {}
  }

  function restoreFromCache(cached) {
      fullResults = cached.results;
      const sel = cached.selections || {};
      scaleSelect.value = sel.scale || "";
      updateMetricOptions();
      metricSelect.value = normalizeMetricId(sel.metric);
      sectionSelect.value = sel.section || "all";

      promptEl.hidden = true;
      errorEl.hidden = true;
      resultsEl.hidden = false;
      if (cached.results && cached.results.model) {
        setModelBarReady(cached.results.model);
        renderConvergence(cached.results.model);
      }
      applySectionView();
      showBiplotControls();
    if (statusTime && cached.computedAt) {
      statusTime.textContent = "Last computed: " + formatComputedTime(cached.computedAt);
    }
  }

  function setExportEnabled(enabled) {
    if (!exportXlsxBtn) return;
    exportXlsxBtn.disabled = !enabled;
    if (enabled) {
      exportXlsxBtn.removeAttribute("title");
    } else {
      exportXlsxBtn.title = "Run gap analysis first";
    }
  }

  function hideResults() {
    fullResults = null;
    resultsEl.hidden = true;
    errorEl.hidden = true;
    hideBiplotControls();
    resetModelBar();
    promptEl.hidden = false;
    setExportEnabled(false);
    statusLeft.textContent = "Awaiting scale & metric selection";
    statusMetric.textContent = "";
    statusTime.textContent = "";
  }

  function showError(msg) {
    errorEl.hidden = false;
    errorText.textContent = msg;
    resetModelBar();
    resultsEl.hidden = true;
    hideBiplotControls();
    promptEl.hidden = true;
    setExportEnabled(false);
    statusLeft.textContent = "Analysis failed";
  }

  function canCompute() {
    return scaleSelect.value && metricSelect.value && !hasSingularBlock();
  }

  function scheduleCompute() {
    clearTimeout(computeTimer);
    if (hasSingularBlock()) {
      applySingularBlock();
      return;
    }
    if (!canCompute()) {
      hideResults();
      clearGapSession();
      return;
    }

    const cached = loadGapSession();
    const current = getSelections();
    if (
      cached &&
      cached.results &&
      cached.sessionId === (meta && meta.session_id) &&
      cached.dataRevision === (meta && meta.data_revision) &&
      cached.filename === (meta && meta.filename) &&
      selectionsMatch(cached.selections, current)
    ) {
      fullResults = cached.results;
      promptEl.hidden = true;
      errorEl.hidden = true;
      resultsEl.hidden = false;
      applySectionView();
      return;
    }

    computeTimer = setTimeout(runCompute, 300);
  }

  function scheduleSectionView() {
    if (!fullResults) return;
    applySectionView();
  }

  async function runCompute() {
    if (!canCompute()) return;

    promptEl.hidden = true;
    errorEl.hidden = true;
    resultsEl.hidden = true;
    setModelBarLoading();
    statusLeft.textContent = "Training MLR on uploaded data…";

    try {
      var restored = await ensureServerUpload();
      if (!restored) {
        throw new Error("No upload data. Please upload a file first.");
      }
      const res = await fetch("/api/gap-analysis/compute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scale: scaleSelect.value,
          metric: metricSelect.value,
        }),
      });
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "Analysis failed.");

      resultsEl.hidden = false;
      sectionSelect.value = "all";
      persistFullResults(data);
      saveSimulationBridge(data);
      setModelBarReady(data.model || {});
      applySectionView();
      resetBiplotView();
    } catch (err) {
      showError(err.message || String(err));
    }
  }

  function renderResults(data, computedAt) {
    const s = data.summary || {};
    const table = data.table || {};
    document.getElementById("stat-sections").textContent = s.sections ?? "—";
    document.getElementById("stat-statements").textContent = s.statements ?? "—";
    const overall =
      (table.sections || []).length > 0
        ? tableOverallCsat(table)
        : s.overall_csat != null
          ? s.overall_csat
          : s.overall_performance;
    document.getElementById("stat-overall").textContent =
      overall != null ? overall + "%" : "—";
    document.getElementById("stat-urgent").textContent = s.fix_urgently ?? "0";

    renderBiplot(data.biplot || []);
    showBiplotControls();
    renderPriority(data.priority_actions || []);
    renderTable(data.table || {});

    const model = data.model || {};
    setModelBarReady(model);
    renderConvergence(model);
    statusLeft.textContent = model.converged
      ? "✓ Model fitted — prediction error settled"
      : model.gd
        ? "Model fitted — stopped at step limit"
        : "Model status unknown";
    statusMetric.textContent =
      "Metric: " + metricDisplayLabel(metricSelect.value, data.metric_label);
    statusTime.textContent =
      "Last computed: " + (computedAt ? formatComputedTime(computedAt) : "just now");
    setExportEnabled(true);
  }

  function renderPriority(actions) {
    priorityList.innerHTML = "";
    priorityList.scrollTop = 0;
    if (priorityCount) {
      priorityCount.textContent = actions.length
        ? actions.length + (actions.length === 1 ? " statement" : " statements")
        : "";
    }
    if (!actions.length) {
      priorityList.innerHTML =
        '<li class="priority-empty">No urgent gaps in this view.</li>';
      return;
    }
    actions.forEach(function (a) {
      const li = document.createElement("li");
      li.className = "priority-item";
      li.innerHTML =
        '<div class="priority-text"><strong>' +
        escapeHtml(a.label) +
        '</strong><span class="priority-sub">' +
        escapeHtml(a.subtitle) +
        "</span></div>";
      priorityList.appendChild(li);
    });
  }

  function formatZ(val) {
    if (val == null || val === "") return "—";
    const n = Number(val);
    if (Number.isNaN(n)) return "—";
    return n.toFixed(3);
  }

  function positionLabel(zPerf, zImp) {
    const zp = Number(zPerf);
    const zi = Number(zImp);
    if (Number.isNaN(zp) || Number.isNaN(zi)) return "—";
    if (zp >= 0 && zi >= 0) return QUADRANT_THEME.maintain.label;
    if (zp < 0 && zi < 0) return QUADRANT_THEME.low.label;
    if (zp < 0 && zi >= 0) return QUADRANT_THEME.urgent.label;
    return QUADRANT_THEME.overkill.label;
  }

  function positionClass(zPerf, zImp) {
    const zp = Number(zPerf);
    const zi = Number(zImp);
    if (zp >= 0 && zi >= 0) return "pos-maintain";
    if (zp < 0 && zi >= 0) return "pos-urgent";
    if (zp >= 0 && zi < 0) return "pos-overkill";
    return "pos-low";
  }

  function quadrantPosClass(stmt) {
    const q = stmt && stmt.quadrant;
    if (q === "urgent" || q === "maintain" || q === "overkill" || q === "low") {
      return "pos-" + q;
    }
    return positionClass(stmt.z_performance, stmt.z_importance);
  }

  function allTableStatements(table) {
    const stmts = [];
    (table.sections || []).forEach(function (sec) {
      (sec.statements || []).forEach(function (stmt) {
        stmts.push(stmt);
      });
    });
    return stmts;
  }

  function tableOverallCsat(table) {
    if (table.overall_csat != null) return table.overall_csat;
    if (table.overall_performance != null) return table.overall_performance;
    const key =
      table.csat_importance_key || csatImportanceKey(sectionSelect.value || "all");
    return sumproductCsat(allTableStatements(table), key);
  }

  function renderCsatRow(label, sectionName, csat, className) {
    const row = document.createElement("tr");
    row.className = className;
    row.innerHTML =
      "<td><strong>" +
      escapeHtml(label) +
      "</strong></td>" +
      "<td>" +
      (sectionName ? escapeHtml(sectionName) : "—") +
      "</td><td><strong>" +
      (csat != null ? csat + "%" : "—") +
      "</strong></td><td>—</td><td>—</td><td>—</td><td>—</td><td>—</td>";
    return row;
  }

  function renderTable(table) {
    tableBody.innerHTML = "";
    const overall = tableOverallCsat(table);

    tableBody.appendChild(
      renderCsatRow("Overall satisfaction", null, overall, "gap-row-overall")
    );

    (table.sections || []).forEach(function (sec) {
      const header = document.createElement("tr");
      header.className = "gap-row-section";
      header.innerHTML =
        '<td colspan="8"><strong>' + escapeHtml(sec.section_name) + "</strong></td>";
      tableBody.appendChild(header);

      (sec.statements || []).forEach(function (stmt) {
        const tr = document.createElement("tr");
        const theme = quadrantTheme(quadrantPosClass(stmt).replace("pos-", ""));
        tr.innerHTML =
          "<td>" +
          escapeHtml(stmt.label) +
          "</td><td>" +
          escapeHtml(sec.section_name) +
          "</td><td>" +
          stmt.performance +
          "%</td><td>" +
          (stmt.importance_section != null ? stmt.importance_section : "—") +
          "%</td><td>" +
          stmt.importance +
          '%</td><td class="z-cell">' +
          formatZ(stmt.z_performance) +
          '</td><td class="z-cell">' +
          formatZ(stmt.z_importance) +
          '</td><td class="position-cell" style="color:' +
          theme.dot +
          ';font-weight:700;">' +
          escapeHtml(positionLabel(stmt.z_performance, stmt.z_importance)) +
          "</td>";
        tableBody.appendChild(tr);
      });
    });
  }

  function computeAxisRange(values) {
    const PAD = 0.45;
    const MIN_HALF = 2.5;

    let extent = MIN_HALF;
    values.forEach(function (v) {
      const n = Number(v);
      if (!Number.isNaN(n)) {
        extent = Math.max(extent, Math.abs(n) + PAD);
      }
    });
    return { min: -extent, max: extent };
  }

  function renderBiplot(points) {
    if (!biplotEl || !window.Plotly) return;

    const xVals = points.map(function (p) {
      return Number(p.z_performance);
    });
    const yVals = points.map(function (p) {
      return Number(p.z_importance);
    });
    // Shared half-extent on both axes so the origin stays centered
    // and quadrants have equal dimensions (matches Excel export / VBA).
    const xRangeRaw = computeAxisRange(xVals);
    const yRangeRaw = computeAxisRange(yVals);
    const half = Math.max(
      Math.abs(xRangeRaw.min),
      Math.abs(xRangeRaw.max),
      Math.abs(yRangeRaw.min),
      Math.abs(yRangeRaw.max)
    );
    const xRange = { min: -half, max: half };
    const yRange = { min: -half, max: half };
    biplotAxisRange = { x: xRange, y: yRange };

    const traces = buildBiplotTraces(points);
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

    const layout = {
      autosize: true,
      height: getBiplotHeight(),
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
      shapes: buildBiplotShapes(xRange, yRange),
      annotations: buildBiplotAnnotations(xRange, yRange),
      hoverlabel: {
        bgcolor: "#ffffff",
        bordercolor: "#e6e8ee",
        font: { color: "#12141a", family: "Plus Jakarta Sans, system-ui, sans-serif", size: 13 },
      },
    };

    const plotPromise = biplotEl.data
      ? window.Plotly.react(biplotEl, traces, layout, BIPLOT_CONFIG)
      : window.Plotly.newPlot(biplotEl, traces, layout, BIPLOT_CONFIG);

    plotPromise.then(scheduleBiplotResize);
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  async function exportXlsx() {
    if (!canCompute() || !fullResults) {
      showError("Run gap analysis first, then export.");
      return;
    }
    if (exportXlsxBtn) {
      exportXlsxBtn.disabled = true;
      exportXlsxBtn.textContent = "Exporting…";
    }
    try {
      const res = await fetch("/api/gap-analysis/export-xlsx", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          scale: scaleSelect.value,
          metric: metricSelect.value,
        }),
      });
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
      let downloadName = "gap_analysis.xlsx";
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
    } catch (err) {
      if (errorEl && errorText) {
        errorText.textContent = err.message || String(err);
        errorEl.hidden = false;
      }
    } finally {
      if (exportXlsxBtn) {
        exportXlsxBtn.textContent = "Export xlsx";
        setExportEnabled(!!fullResults);
      }
    }
  }

  if (exportXlsxBtn) {
    exportXlsxBtn.addEventListener("click", exportXlsx);
  }

  scaleSelect.addEventListener("change", function () {
    updateMetricOptions();
    metricSelect.value = "";
    scheduleCompute();
  });

  metricSelect.addEventListener("change", scheduleCompute);
  sectionSelect.addEventListener("change", scheduleSectionView);

  if (modelQualityBtn) {
    modelQualityBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      toggleModelQualityPanel();
    });
  }

  document.addEventListener("click", function () {
    if (modelQualityPanel && !modelQualityPanel.hidden) {
      modelQualityPanel.hidden = true;
      if (modelQualityBtn) {
        modelQualityBtn.setAttribute("aria-expanded", "false");
        modelQualityBtn.classList.remove("is-open");
      }
      if (loadingEl) loadingEl.classList.remove("is-quality-open");
    }
  });

  if (modelQualityPanel) {
    modelQualityPanel.addEventListener("click", function (e) {
      e.stopPropagation();
    });
  }

  async function init() {
    const hasUpload = window.gapAnalyzerSessionReady
      ? await window.gapAnalyzerSessionReady
      : false;
    if (!hasUpload) {
      if (scaleSelect) scaleSelect.disabled = true;
      if (metricSelect) metricSelect.disabled = true;
      if (sectionSelect) sectionSelect.disabled = true;
      if (promptEl) {
        promptEl.hidden = false;
        const copy = promptEl.querySelector("p");
        if (copy) {
          copy.innerHTML =
            'Upload a survey file first on the <a href="/upload">Upload</a> page.';
        }
      }
      return;
    }

    await loadMeta();
    if (hasSingularBlock()) {
      return;
    }
    const cached = loadGapSession();
    if (
      cached &&
      cached.results &&
      cached.sessionId === meta.session_id &&
      cached.dataRevision === meta.data_revision &&
      cached.filename === meta.filename &&
      cached.selections &&
      cached.selections.scale &&
      cached.selections.metric
    ) {
      fullResults = cached.results;
      const sel = cached.selections || {};
      scaleSelect.value = sel.scale || "";
      updateMetricOptions();
      metricSelect.value = normalizeMetricId(sel.metric);
      sectionSelect.value = sel.section || "all";
      promptEl.hidden = true;
      errorEl.hidden = true;
      resultsEl.hidden = false;
      if (cached.results && cached.results.model) {
        setModelBarReady(cached.results.model);
        renderConvergence(cached.results.model);
      }
      applySectionView();
      try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(cached));
      } catch (e) {}
      if (statusTime) {
        statusTime.textContent =
          "Last computed: " + formatComputedTime(cached.computedAt);
      }
      return;
    }
    hideResults();
  }

  init().catch(function (err) {
    showError(err.message || String(err));
  });
})();
