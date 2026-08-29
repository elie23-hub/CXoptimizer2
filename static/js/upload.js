/**
 * Upload — progress bar, sessionStorage for in-tab navigation, reset on reload.
 */

(function () {
  const STORAGE_KEY = "gapAnalyzer_upload_session";
  const GAP_STORAGE_KEY = "gapAnalyzer_gap_session";
  const STORAGE_VERSION = 18;

  const fileInput = document.getElementById("survey_file");
  const browseRow = document.getElementById("file-browse-row");
  const browseFill = document.getElementById("browse-fill");
  const browseLabel = document.getElementById("browse-label");
  const resultsContainer = document.getElementById("results-container");

  if (!fileInput) return;

  let progressTimer = null;
  let sectionSaveTimer = null;
  let savedFilename = "";

  function isPageReload() {
    const nav = performance.getEntriesByType("navigation")[0];
    return !nav || nav.type === "reload";
  }

  function getResultsHtml() {
    const stack = resultsContainer && resultsContainer.querySelector(".results-stack");
    return stack ? stack.innerHTML : "";
  }

  function collectSectionNames() {
    const names = {};
    document.querySelectorAll(".structure-name-input").forEach(function (input) {
      names[input.dataset.section] = input.value.trim();
    });
    return names;
  }

  function applySectionNames(names) {
    if (!names) return;
    document.querySelectorAll(".structure-name-input").forEach(function (input) {
      const key = input.dataset.section;
      if (Object.prototype.hasOwnProperty.call(names, key)) {
        input.value = names[key];
      }
    });
  }

  function saveSession(filename, html, sectionNames) {
    if (!resultsContainer || !resultsContainer.classList.contains("has-results")) {
      return;
    }
    try {
      sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          version: STORAGE_VERSION,
          filename: filename || savedFilename,
          html: html !== undefined ? html : getResultsHtml(),
          sectionNames: sectionNames || collectSectionNames(),
        })
      );
    } catch (e) {}
  }

  function syncSessionStorage() {
    saveSession();
  }

  function clearSession() {
    sessionStorage.removeItem(STORAGE_KEY);
    sessionStorage.removeItem(GAP_STORAGE_KEY);
    sessionStorage.removeItem("gapAnalyzer_sim_summary");
  }

  async function resetServerSession() {
    try {
      await fetch("/api/session/reset", { method: "POST" });
    } catch (e) {}
  }

  async function fetchSectionNamesFromServer() {
    try {
      const response = await fetch("/api/section-names");
      const data = await response.json();
      if (data.ok && data.names) {
        applySectionNames(data.names);
        syncSessionStorage();
      }
    } catch (e) {}
  }

  async function restoreSession() {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const data = JSON.parse(raw);
      if (!data.html || data.version !== STORAGE_VERSION) {
        clearSession();
        return;
      }

      savedFilename = data.filename || "";
      showProgressComplete(savedFilename);
      showResults(data.html, false);
      applySectionNames(data.sectionNames || {});
      updateHeaderBadge(data.filename);
      bindReplaceHandler();
      bindSectionNameInputs();
      bindQuestionLabelSearch();
      bindDataPreviewSort();
      bindSummaryStatsToggle();
      await fetchSectionNamesFromServer();
    } catch (e) {
      clearSession();
    }
  }

  if (isPageReload()) {
    clearSession();
    resetServerSession();
    resetBrowseBar();
    const badge = document.querySelector(".file-badge");
    if (badge) badge.remove();
  } else {
    restoreSession();
  }

  function setProgress(percent) {
    if (browseFill) browseFill.style.width = percent + "%";
  }

  function setRowState(state) {
    if (!browseRow) return;
    browseRow.classList.remove("is-uploading", "is-complete", "is-error");
    if (state) browseRow.classList.add(state);
  }

  function startProgress(filename) {
    savedFilename = filename;
    setRowState("is-uploading");
    setProgress(0);
    if (browseLabel) browseLabel.textContent = "Uploading…";

    clearInterval(progressTimer);
    let p = 0;
    progressTimer = setInterval(function () {
      p += Math.random() * 8 + 3;
      if (p > 90) p = 90;
      setProgress(p);
    }, 150);
  }

  function showProgressComplete(filename) {
    clearInterval(progressTimer);
    setRowState("is-complete");
    setProgress(100);
    if (browseLabel) browseLabel.textContent = "Upload complete";
    if (filename && browseRow) browseRow.dataset.filename = filename;
  }

  function showProgressError() {
    clearInterval(progressTimer);
    setRowState("is-error");
    setProgress(100);
    if (browseLabel) browseLabel.textContent = "Upload failed";
  }

  function resetBrowseBar() {
    setRowState("");
    setProgress(0);
    if (browseLabel) browseLabel.textContent = "No file chosen";
    if (browseRow) browseRow.dataset.filename = "";
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function updateHeaderBadge(filename) {
    if (!filename) return;
    let badge = document.querySelector(".file-badge");
    if (!badge) {
      const header = document.querySelector(".top-header");
      if (header) {
        badge = document.createElement("span");
        badge.className = "file-badge";
        header.appendChild(badge);
      }
    }
    if (badge) badge.textContent = filename;
  }

  function showResults(html, scroll) {
    if (!resultsContainer) return;
    resultsContainer.innerHTML = '<div class="results-stack">' + html + "</div>";
    resultsContainer.classList.add("has-results");
    if (scroll !== false) {
      resultsContainer.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function showError(message) {
    showProgressError();
    showResults(
      '<section class="card error-card">' +
        '<div class="error-card-header"><span class="error-icon">✗</span>' +
        '<div><strong class="error-title">Could not process file</strong></div></div>' +
        '<p class="error-detail">' + escapeHtml(message) + "</p></section>"
    );
    clearSession();
  }

  async function uploadFile(file) {
    if (!file) {
      showError("Please choose a file first.");
      return;
    }

    clearSession();
    if (resultsContainer) {
      resultsContainer.innerHTML = "";
      resultsContainer.classList.remove("has-results");
    }

    startProgress(file.name);

    const formData = new FormData();
    formData.append("survey_file", file);

    try {
      const response = await fetch("/api/upload", { method: "POST", body: formData });
      let data;
      try {
        data = await response.json();
      } catch (e) {
        showError("Server returned an invalid response. Restart the app and try again.");
        return;
      }

      if (!response.ok || !data.ok) {
        showError(data.error || "Upload failed. Please try again.");
        return;
      }

      const html = (data.html || "").trim();
      if (!html) {
        showError(data.error || "No preview could be generated. Check column names.");
        return;
      }

      clearInterval(progressTimer);
      setProgress(100);
      showProgressComplete(file.name);

      showResults(html);
      saveSession(data.filename, html, {});
      updateHeaderBadge(data.filename);
      bindReplaceHandler();
      bindSectionNameInputs();
      bindQuestionLabelSearch();
      bindDataPreviewSort();
      bindSummaryStatsToggle();
    } catch (err) {
      showError("Could not reach the server. Run: python app.py");
    } finally {
      fileInput.value = "";
    }
  }

  function bindReplaceHandler() {
    const replace = document.getElementById("replace_file");
    if (!replace) return;
    const newReplace = replace.cloneNode(true);
    replace.parentNode.replaceChild(newReplace, replace);
    newReplace.addEventListener("change", function () {
      if (newReplace.files && newReplace.files[0]) {
        uploadFile(newReplace.files[0]);
      }
    });
  }

  async function persistSectionNames() {
    const names = collectSectionNames();
    if (!Object.keys(names).length) return;
    syncSessionStorage();
    try {
      await fetch("/api/section-names", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ names: names }),
      });
    } catch (e) {}
  }

  function scheduleSectionNameSave() {
    clearTimeout(sectionSaveTimer);
    sectionSaveTimer = setTimeout(function () {
      syncSessionStorage();
      persistSectionNames();
    }, 400);
  }

  function bindSectionNameInputs() {
    document.querySelectorAll(".structure-name-input").forEach(function (input) {
      const clone = input.cloneNode(true);
      input.parentNode.replaceChild(clone, input);
      clone.addEventListener("input", scheduleSectionNameSave);
      clone.addEventListener("blur", function () {
        syncSessionStorage();
        persistSectionNames();
      });
    });
  }

  function bindQuestionLabelSearch() {
    const card = document.querySelector(".question-labels-card");
    if (!card) return;

    const searchInput = card.querySelector(".question-label-search");
    const tbody = card.querySelector(".question-labels-table tbody");
    const visibleCount = card.querySelector(".question-labels-visible");
    if (!searchInput || !tbody) return;

    function variableMatches(variable, query) {
      if (!query) return true;
      const v = variable.toLowerCase();
      const q = query.toLowerCase();
      if (v.includes(q)) return true;
      // Section shorthand: "S1" matches S1_Q1, S1_Q2, …
      const section = q.match(/^s(\d+)$/i);
      if (section) {
        return v.startsWith("s" + section[1] + "_");
      }
      return false;
    }

    function filterRows() {
      const query = searchInput.value.trim();
      const rows = tbody.querySelectorAll(".question-label-row");
      let shown = 0;
      rows.forEach(function (row) {
        const variable = row.getAttribute("data-variable") || "";
        const match = variableMatches(variable, query);
        row.classList.toggle("is-hidden", !match);
        if (match) shown += 1;
      });
      if (visibleCount) visibleCount.textContent = String(shown);
    }

    searchInput.addEventListener("input", filterRows);
    searchInput.addEventListener("search", filterRows);
  }

  function bindDataPreviewSort() {
    const table = document.getElementById("data-preview-table");
    if (!table) return;

    const tbody = table.querySelector("tbody");
    if (!tbody) return;

    tbody.querySelectorAll("tr").forEach(function (row, idx) {
      row.setAttribute("data-orig-idx", String(idx));
    });

    function cellValue(row, colIdx) {
      const cell = row.querySelector('td[data-col-idx="' + colIdx + '"]');
      if (!cell) return "";
      return (cell.textContent || "").trim();
    }

    function compareValues(a, b) {
      const na = Number(a);
      const nb = Number(b);
      const aNum = a !== "" && !Number.isNaN(na);
      const bNum = b !== "" && !Number.isNaN(nb);
      if (aNum && bNum) return na - nb;
      return a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" });
    }

    function setArrow(btn, sort) {
      const arrow = btn.querySelector(".sort-arrows");
      if (!arrow) return;
      arrow.textContent = sort === "asc" ? "↑" : sort === "desc" ? "↓" : "⇅";
    }

    table.querySelectorAll(".th-sort-btn").forEach(function (btn) {
      const fresh = btn.cloneNode(true);
      btn.parentNode.replaceChild(fresh, btn);

      fresh.addEventListener("click", function () {
        const colIdx = fresh.getAttribute("data-col-idx");
        const current = fresh.getAttribute("data-sort") || "none";
        const next = current === "none" ? "asc" : current === "asc" ? "desc" : "none";

        table.querySelectorAll(".th-sort-btn").forEach(function (other) {
          if (other !== fresh) {
            other.setAttribute("data-sort", "none");
            setArrow(other, "none");
          }
        });
        fresh.setAttribute("data-sort", next);
        setArrow(fresh, next);

        const rows = Array.from(tbody.querySelectorAll("tr"));
        if (next === "none") {
          rows.sort(function (a, b) {
            return Number(a.getAttribute("data-orig-idx")) - Number(b.getAttribute("data-orig-idx"));
          });
        } else {
          const dir = next === "asc" ? 1 : -1;
          rows.sort(function (a, b) {
            return compareValues(cellValue(a, colIdx), cellValue(b, colIdx)) * dir;
          });
        }

        rows.forEach(function (row) {
          tbody.appendChild(row);
        });
      });
    });
  }

  function setSummaryStatsOpen(open) {
    const btn = document.getElementById("summary-stats-btn");
    const panel = document.getElementById("summary-stats-panel");
    if (!panel) return;

    panel.classList.toggle("is-open", open);
    panel.hidden = !open;
    if (btn) {
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      btn.classList.toggle("is-active", open);
    }
    if (open) {
      renderRespondentCvChart();
      renderRespondentCvNormalChart();
    }
  }

  function bindSummaryStatsToggle() {
    const btn = document.getElementById("summary-stats-btn");
    const panel = document.getElementById("summary-stats-panel");
    if (!btn || !panel) return;

    setSummaryStatsOpen(false);

    const fresh = btn.cloneNode(true);
    btn.parentNode.replaceChild(fresh, btn);

    fresh.addEventListener("click", function () {
      const isOpen = panel.classList.contains("is-open");
      setSummaryStatsOpen(!isOpen);
    });
  }

  function renderRespondentCvChart() {
    const svg = document.getElementById("respondent-cv-chart");
    const dataEl = document.getElementById("respondent-cv-data");
    if (!svg || !dataEl) return;

    let data;
    try {
      data = JSON.parse(dataEl.textContent || "{}");
    } catch (e) {
      return;
    }

    const points = data.points || [];
    if (!points.length) return;

    const hasIdColumn = Boolean(data.id_column);
    const slotWidth = 32;
    const pad = { top: 16, right: 24, bottom: 64, left: 84 };
    const plotW = points.length * slotWidth;
    const w = pad.left + plotW + pad.right;
    const h = 280;
    const plotH = h - pad.top - pad.bottom;
    let yMin = Infinity;
    let yMax = -Infinity;
    points.forEach(function (p) {
      if (p.cv < yMin) yMin = p.cv;
      if (p.cv > yMax) yMax = p.cv;
    });
    if (!Number.isFinite(yMin) || !Number.isFinite(yMax)) return;
    if (yMin === yMax) {
      yMin = Math.max(0, yMin - 0.05);
      yMax = yMax + 0.05;
    } else {
      const yPad = (yMax - yMin) * 0.08;
      yMin = Math.max(0, yMin - yPad);
      yMax = yMax + yPad;
    }

    function xScaleAt(i) {
      return pad.left + (i + 0.5) * slotWidth;
    }
    function yScale(v) {
      return pad.top + plotH - ((v - yMin) / (yMax - yMin || 1)) * plotH;
    }

    const ns = "http://www.w3.org/2000/svg";
    function el(name, attrs) {
      const node = document.createElementNS(ns, name);
      Object.keys(attrs || {}).forEach(function (key) {
        node.setAttribute(key, attrs[key]);
      });
      return node;
    }

    svg.setAttribute("width", String(w));
    svg.setAttribute("height", String(h));
    svg.removeAttribute("viewBox");
    svg.innerHTML = "";

    const yTicks = 5;
    for (let i = 0; i <= yTicks; i += 1) {
      const val = yMin + ((yMax - yMin) * i) / yTicks;
      const y = yScale(val);
      svg.appendChild(
        el("line", {
          x1: String(pad.left),
          y1: String(y),
          x2: String(pad.left + plotW),
          y2: String(y),
          class: "cv-grid",
        })
      );
      const label = el("text", {
        x: String(pad.left - 8),
        y: String(y + 4),
        class: "cv-axis-label",
        "text-anchor": "end",
      });
      label.textContent = val.toFixed(3);
      svg.appendChild(label);
    }

    svg.appendChild(
      el("line", {
        x1: String(pad.left),
        y1: String(pad.top + plotH),
        x2: String(pad.left + plotW),
        y2: String(pad.top + plotH),
        class: "cv-axis",
      })
    );
    svg.appendChild(
      el("line", {
        x1: String(pad.left),
        y1: String(pad.top),
        x2: String(pad.left),
        y2: String(pad.top + plotH),
        class: "cv-axis",
      })
    );

    points.forEach(function (p, i) {
      const cx = xScaleAt(i);
      const cy = yScale(p.cv);

      svg.appendChild(
        el("line", {
          x1: String(cx),
          y1: String(pad.top + plotH),
          x2: String(cx),
          y2: String(pad.top + plotH + 5),
          class: "cv-axis-tick",
        })
      );
      const tickY = pad.top + plotH + 16;
      const tickLabel = el("text", {
        x: String(cx),
        y: String(tickY),
        class: "cv-x-tick-label",
        "text-anchor": "end",
        transform: "rotate(-55 " + cx + " " + tickY + ")",
      });
      tickLabel.textContent = hasIdColumn ? String(p.label) : String(p.index);
      svg.appendChild(tickLabel);

      const dot = el("circle", {
        cx: String(cx),
        cy: String(cy),
        r: points.length > 400 ? "2" : "3",
        class: "cv-point",
      });
      const title = el("title");
      title.textContent =
        (hasIdColumn ? "ID " + p.label : "Respondent " + p.index) +
        " (row " +
        p.index +
        ") · CV " +
        p.cv;
      dot.appendChild(title);
      svg.appendChild(dot);
    });

    const xLabel = el("text", {
      x: String(pad.left + plotW / 2),
      y: String(h - 6),
      class: "cv-axis-label",
      "text-anchor": "middle",
    });
    xLabel.textContent = hasIdColumn ? "Respondent ID" : "Respondent index";
    svg.appendChild(xLabel);

    const yLabel = el("text", {
      x: String(16),
      y: String(pad.top + plotH / 2),
      class: "cv-axis-label cv-axis-title",
      "text-anchor": "middle",
      transform: "rotate(-90 16 " + (pad.top + plotH / 2) + ")",
    });
    yLabel.textContent = "CV (stdev / mean)";
    svg.appendChild(yLabel);
  }

  function renderRespondentCvNormalChart() {
    const svg = document.getElementById("respondent-cv-normal-chart");
    const dataEl = document.getElementById("respondent-cv-data");
    if (!svg || !dataEl) return;

    let data;
    try {
      data = JSON.parse(dataEl.textContent || "{}");
    } catch (e) {
      return;
    }

    const points = data.points || [];
    if (!points.length) return;

    const hasIdColumn = Boolean(data.id_column);
    const cvs = points.map(function (p) {
      return Number(p.cv);
    });
    const mean = cvs.reduce(function (a, b) {
      return a + b;
    }, 0) / cvs.length;
    const variance =
      cvs.reduce(function (sum, value) {
        const diff = value - mean;
        return sum + diff * diff;
      }, 0) / cvs.length;
    const std = Math.sqrt(variance);

    function normalPdf(z) {
      return Math.exp(-0.5 * z * z) / Math.sqrt(2 * Math.PI);
    }

    const zPoints = points.map(function (p) {
      const z = std > 0 ? (Number(p.cv) - mean) / std : 0;
      return {
        index: p.index,
        label: p.label,
        cv: Number(p.cv),
        z: z,
        density: normalPdf(z),
      };
    });

    const pad = { top: 16, right: 24, bottom: 52, left: 84 };
    const w = 640;
    const h = 280;
    const plotW = w - pad.left - pad.right;
    const plotH = h - pad.top - pad.bottom;

    // Keep a fixed normal window so the bell is fully visible.
    // Extreme outlier z-scores are clamped to the plot edges.
    const zMin = -3.5;
    const zMax = 3.5;

    const yMax = normalPdf(0) * 1.08;

    function clampZ(z) {
      return Math.max(zMin, Math.min(zMax, z));
    }
    function xScale(z) {
      return pad.left + ((z - zMin) / (zMax - zMin || 1)) * plotW;
    }
    function yScale(density) {
      return pad.top + plotH - (density / yMax) * plotH;
    }

    const ns = "http://www.w3.org/2000/svg";
    function el(name, attrs) {
      const node = document.createElementNS(ns, name);
      Object.keys(attrs || {}).forEach(function (key) {
        node.setAttribute(key, attrs[key]);
      });
      return node;
    }

    svg.setAttribute("viewBox", "0 0 " + w + " " + h);
    svg.setAttribute("width", "100%");
    svg.setAttribute("height", String(h));
    svg.innerHTML = "";

    const yTicks = 4;
    for (let i = 0; i <= yTicks; i += 1) {
      const val = (yMax * i) / yTicks;
      const y = yScale(val);
      svg.appendChild(
        el("line", {
          x1: String(pad.left),
          y1: String(y),
          x2: String(pad.left + plotW),
          y2: String(y),
          class: "cv-grid",
        })
      );
      const label = el("text", {
        x: String(pad.left - 8),
        y: String(y + 4),
        class: "cv-axis-label",
        "text-anchor": "end",
      });
      label.textContent = val.toFixed(3);
      svg.appendChild(label);
    }

    const xTicks = 6;
    for (let i = 0; i <= xTicks; i += 1) {
      const z = zMin + ((zMax - zMin) * i) / xTicks;
      const x = xScale(z);
      svg.appendChild(
        el("line", {
          x1: String(x),
          y1: String(pad.top),
          x2: String(x),
          y2: String(pad.top + plotH),
          class: "cv-grid",
        })
      );
      const tickLabel = el("text", {
        x: String(x),
        y: String(pad.top + plotH + 18),
        class: "cv-axis-label",
        "text-anchor": "middle",
      });
      tickLabel.textContent = z.toFixed(1);
      svg.appendChild(tickLabel);
    }

    svg.appendChild(
      el("line", {
        x1: String(pad.left),
        y1: String(pad.top + plotH),
        x2: String(pad.left + plotW),
        y2: String(pad.top + plotH),
        class: "cv-axis",
      })
    );
    svg.appendChild(
      el("line", {
        x1: String(pad.left),
        y1: String(pad.top),
        x2: String(pad.left),
        y2: String(pad.top + plotH),
        class: "cv-axis",
      })
    );

    function percentile(sorted, p) {
      if (!sorted.length) return 0;
      const idx = (sorted.length - 1) * p;
      const lo = Math.floor(idx);
      const hi = Math.ceil(idx);
      if (lo === hi) return sorted[lo];
      return sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo);
    }

    const zSorted = zPoints
      .map(function (p) {
        return p.z;
      })
      .sort(function (a, b) {
        return a - b;
      });
    const q1 = percentile(zSorted, 0.25);
    const q3 = percentile(zSorted, 0.75);
    const baseY = pad.top + plotH;

    const q1Plot = clampZ(q1);
    const q3Plot = clampZ(q3);
    if (q3Plot > q1Plot) {
      const iqrSteps = 80;
      let fillD = "M " + xScale(q1Plot) + " " + baseY;
      fillD += " L " + xScale(q1Plot) + " " + yScale(normalPdf(q1Plot));
      for (let i = 0; i <= iqrSteps; i += 1) {
        const z = q1Plot + ((q3Plot - q1Plot) * i) / iqrSteps;
        fillD += " L " + xScale(z) + " " + yScale(normalPdf(z));
      }
      fillD += " L " + xScale(q3Plot) + " " + baseY + " Z";
      svg.appendChild(
        el("path", {
          d: fillD,
          class: "cv-curve-iqr-fill",
        })
      );
    }

    // Draw points under the curve so the full bell stroke stays visible.
    zPoints.forEach(function (p) {
      const zPlot = clampZ(p.z);
      const density = normalPdf(zPlot);
      const dot = el("circle", {
        cx: String(xScale(zPlot)),
        cy: String(yScale(density)),
        r: zPoints.length > 400 ? "1.75" : "2.5",
        class: "cv-point",
        opacity: zPoints.length > 400 ? "0.55" : "0.75",
      });
      const title = el("title");
      title.textContent =
        (hasIdColumn ? "ID " + p.label : "Respondent " + p.index) +
        " · CV " +
        p.cv.toFixed(4) +
        " · z " +
        p.z.toFixed(3) +
        " · density " +
        p.density.toFixed(4);
      dot.appendChild(title);
      svg.appendChild(dot);
    });

    const curveSteps = 160;
    let pathD = "";
    for (let i = 0; i <= curveSteps; i += 1) {
      const z = zMin + ((zMax - zMin) * i) / curveSteps;
      const x = xScale(z);
      const y = yScale(normalPdf(z));
      pathD += (i === 0 ? "M" : "L") + x + " " + y + " ";
    }
    svg.appendChild(
      el("path", {
        d: pathD.trim(),
        class: "cv-curve",
      })
    );

    const xLabel = el("text", {
      x: String(pad.left + plotW / 2),
      y: String(h - 8),
      class: "cv-axis-label",
      "text-anchor": "middle",
    });
    xLabel.textContent = "CV z-score";
    svg.appendChild(xLabel);

    const yLabel = el("text", {
      x: String(16),
      y: String(pad.top + plotH / 2),
      class: "cv-axis-label cv-axis-title",
      "text-anchor": "middle",
      transform: "rotate(-90 16 " + (pad.top + plotH / 2) + ")",
    });
    yLabel.textContent = "Normal density";
    svg.appendChild(yLabel);
  }

  fileInput.addEventListener("change", function () {
    if (fileInput.files && fileInput.files[0]) {
      uploadFile(fileInput.files[0]);
    }
  });
})();
