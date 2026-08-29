/**
 * Summary — review top-down simulation changes from session JSON.
 */

(function () {
  const STORAGE_KEY = "gapAnalyzer_sim_summary";

  const promptEl = document.getElementById("sum-prompt");
  const promptText = document.getElementById("sum-prompt-text");
  const errorEl = document.getElementById("sum-error");
  const errorText = document.getElementById("sum-error-text");
  const workspaceEl = document.getElementById("sum-workspace");
  const pageMetaEl = document.getElementById("sum-page-meta");
  const leadEl = document.getElementById("sum-sim-lead");
  const subEl = document.getElementById("sum-sim-sub");
  const legendEl = document.getElementById("sum-sim-legend");
  const barListEl = document.getElementById("sum-bar-list");
  const statusLeft = document.getElementById("sum-status-left");
  const statusDetail = document.getElementById("sum-status-detail");
  const statusRight = document.getElementById("sum-status-right");

  if (!barListEl) return;

  const QUADRANT_META = {
    urgent: {
      title: "Urgent",
      blurb: "low performance high importance",
      tone: "urgent",
    },
    maintain: {
      title: "Maintain",
      blurb: "high performance high importance",
      tone: "maintain",
    },
    low: {
      title: "Low priority",
      blurb: "low performance low importance",
      tone: "low",
    },
    overkill: {
      title: "Overkill",
      blurb: "high performance low importance",
      tone: "overkill",
    },
  };

  let meta = null;
  let stored = null;

  function escapeHtml(str) {
    return String(str == null ? "" : str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatPct(val) {
    const n = Number(val);
    if (Number.isNaN(n)) return "—";
    return Math.round(n) + "%";
  }

  function formatPctExact(val) {
    const n = Number(val);
    if (Number.isNaN(n)) return "—";
    if (Math.abs(n - Math.round(n)) < 0.05) return Math.round(n) + "%";
    return (Math.round(n * 10) / 10) + "%";
  }

  function showError(msg) {
    if (errorEl && errorText) {
      errorText.textContent = msg;
      errorEl.hidden = false;
    }
    if (workspaceEl) workspaceEl.hidden = true;
    if (promptEl) promptEl.hidden = true;
  }

  function hideError() {
    if (errorEl) errorEl.hidden = true;
  }

  function showPrompt(html) {
    hideError();
    if (promptText) promptText.innerHTML = html;
    if (promptEl) promptEl.hidden = false;
    if (workspaceEl) workspaceEl.hidden = true;
  }

  function readStoredState() {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (e) {
      return null;
    }
  }

  function relativeRunLabel(ts) {
    if (!ts) return "run just now";
    const mins = Math.max(0, Math.round((Date.now() - Number(ts)) / 60000));
    if (mins < 1) return "run just now";
    if (mins === 1) return "run 1 min ago";
    if (mins < 60) return "run " + mins + " mins ago";
    const hours = Math.round(mins / 60);
    if (hours === 1) return "run 1 hour ago";
    return "run " + hours + " hours ago";
  }

  function metricLabel(raw) {
    if (!raw) return "";
    const key = String(raw).toLowerCase();
    if (key === "top2" || key.indexOf("top-2") !== -1 || key.indexOf("top 2") !== -1) {
      return "top-2-box";
    }
    if (key === "top3" || key.indexOf("top-3") !== -1) return "top-3-box";
    if (key === "mean" || key === "weighted") return "mean";
    return String(raw);
  }

  function renderPageMeta() {
    if (!pageMetaEl || !meta) return;
    const parts = [];
    if (meta.filename) parts.push(meta.filename);
    const respondents = meta.respondents != null ? meta.respondents : meta.model && meta.model.n_respondents;
    if (respondents != null) parts.push(respondents + " responses");
    parts.push(relativeRunLabel(stored && stored.saved_at));
    pageMetaEl.textContent = parts.join(" · ");
  }

  function renderStatusBar() {
    if (statusLeft) statusLeft.textContent = "Summary";
    const bits = [];
    const metric = metricLabel(meta && (meta.metric_label || meta.metric));
    if (metric) bits.push("Metric: " + metric);
    if (meta && meta.kept_rows != null && meta.raw_rows != null) {
      bits.push(meta.kept_rows + " of " + meta.raw_rows + " responses kept");
    } else if (meta && meta.respondents != null) {
      bits.push(meta.respondents + " responses");
    }
    if (statusDetail) statusDetail.textContent = bits[0] || "";
    if (statusRight) statusRight.textContent = bits.slice(1).join(" · ");
  }

  function barWidths(from, to) {
    const a = Math.max(0, Math.min(100, Number(from) || 0));
    const b = Math.max(0, Math.min(100, Number(to) || 0));
    return { before: a, after: b };
  }

  function renderBarRow(row) {
    const from = Number(row.performance);
    const to = Number(row.required_performance);
    const widths = barWidths(from, to);
    const tone = row.tone || row.quadrant || "improved";
    return (
      '<div class="sum-bar-row">' +
      '<div class="sum-bar-label">' +
      escapeHtml(row.label) +
      "</div>" +
      '<div class="sum-bar-lines">' +
      '<div class="sum-bar-line">' +
      '<div class="sum-bar-fill" style="width:' +
      widths.before +
      '%">' +
      '<span class="sum-bar sum-bar--before"></span>' +
      "</div>" +
      '<span class="sum-bar-pct sum-bar-pct--before">' +
      escapeHtml(formatPct(from)) +
      "</span>" +
      "</div>" +
      '<div class="sum-bar-line">' +
      '<div class="sum-bar-fill" style="width:' +
      widths.after +
      '%">' +
      '<span class="sum-bar sum-bar--after sum-bar--' +
      escapeHtml(tone) +
      '"></span>' +
      "</div>" +
      '<span class="sum-bar-pct sum-bar-pct--after">' +
      escapeHtml(formatPct(to)) +
      "</span>" +
      "</div>" +
      "</div></div>"
    );
  }

  function renderLegend(items) {
    if (!legendEl) return;
    if (!items || !items.length) {
      legendEl.hidden = true;
      legendEl.innerHTML = "";
      return;
    }
    legendEl.hidden = false;
    legendEl.innerHTML = items
      .map(function (item) {
        return (
          '<span class="sum-legend-item sum-legend-' +
          escapeHtml(item.tone) +
          '"><i></i>' +
          escapeHtml(item.label) +
          "</span>"
        );
      })
      .join("");
  }

  function renderTopDown() {
    const td = (stored && stored.top_down_result) || null;
    if (!td) {
      showPrompt(
        'No top-down simulation saved yet. Open <a href="/simulation">simulation</a>, ' +
          "choose Top-down, set a target and quadrant, then return here."
      );
      return;
    }

    if (promptEl) promptEl.hidden = true;
    if (workspaceEl) workspaceEl.hidden = false;

    const quadrants = td.quadrants || stored.top_down_quadrants || [];
    const qMeta = quadrants
      .map(function (q) {
        return QUADRANT_META[q];
      })
      .filter(Boolean);
    const qTitles = qMeta.map(function (q) {
      return q.title;
    });
    const qTitleHtml = qTitles.length
      ? qTitles
          .map(function (t, i) {
            const tone = (qMeta[i] && qMeta[i].tone) || "urgent";
            return (
              '<strong class="sum-q-chip sum-q-chip--' +
              escapeHtml(tone) +
              '">' +
              escapeHtml(t) +
              "</strong>"
            );
          })
          .join(", ")
      : "<strong>selected</strong>";

    const baseline =
      td.baseline_overall != null
        ? td.baseline_overall
        : stored && stored.baseline_overall != null
          ? stored.baseline_overall
          : meta && meta.baseline_overall;

    if (leadEl) {
      const targetHtml =
        "<strong>" + escapeHtml(formatPctExact(td.target_overall)) + "</strong>";
      const achievedHtml =
        '<strong class="sum-pct-after">' +
        escapeHtml(formatPctExact(td.achieved_overall)) +
        "</strong>";
      const fromHtml =
        baseline != null
          ? "from <strong>" +
            escapeHtml(formatPctExact(baseline)) +
            "</strong> to reach " +
            targetHtml
          : "to reach " + targetHtml;
      leadEl.innerHTML =
        "You wanted to increase the overall satisfaction " +
        fromHtml +
        ", allowing changes only within the " +
        qTitleHtml +
        " quadrant" +
        (qTitles.length === 1 ? "" : "s") +
        ". Achieved " +
        achievedHtml +
        ".";
    }

    const changed = td.changed_statements || [];
    if (subEl) {
      if (!qMeta.length) {
        subEl.textContent = "No quadrant was selected for this run.";
      } else {
        const blurbs = qMeta
          .map(function (q) {
            return q.title + " (" + q.blurb + ")";
          })
          .join("; ");
        subEl.textContent =
          blurbs +
          ": only statements in " +
          (qTitles.length === 1 ? "this quadrant were" : "these quadrants were") +
          " adjusted; " +
          changed.length +
          " statement" +
          (changed.length === 1 ? "" : "s") +
          " changed.";
      }
    }

    const legendTones = {};
    changed.forEach(function (row) {
      const tone = row.quadrant || "urgent";
      legendTones[tone] = true;
    });
    const legendItems = [{ tone: "before", label: "before" }];
    Object.keys(legendTones).forEach(function (tone) {
      const info = QUADRANT_META[tone];
      legendItems.push({
        tone: tone,
        label: "after · " + ((info && info.title) || tone).toLowerCase(),
      });
    });
    renderLegend(legendItems);

    if (!changed.length) {
      barListEl.innerHTML =
        '<p class="sum-bar-empty">No statement scores changed in the saved top-down run.</p>';
      return;
    }

    barListEl.innerHTML = changed
      .map(function (row) {
        return renderBarRow({
          label: row.label,
          performance: row.performance,
          required_performance: row.required_performance,
          tone: row.quadrant || "urgent",
        });
      })
      .join("");
  }

  async function init() {
    stored = readStoredState();

    try {
      const hasUpload = window.gapAnalyzerSessionReady
        ? await window.gapAnalyzerSessionReady
        : false;
      if (!hasUpload) {
        showPrompt(
          'Upload a survey file first on the <a href="/upload">Upload</a> page.'
        );
        return;
      }

      const res = await fetch("/api/simulation/meta");
      const data = await res.json();
      if (!data.ok) {
        if (data.needs_gap_analysis) {
          showPrompt(
            'Run <a href="/gap-analysis">gap analysis</a> first, then open ' +
              '<a href="/simulation">simulation</a> to prepare a summary.'
          );
          return;
        }
        if (/no upload/i.test(data.error || "")) {
          showPrompt(
            'Upload a survey file first on the <a href="/upload">Upload</a> page.'
          );
          return;
        }
        throw new Error(data.error || "Could not load simulation data.");
      }

      meta = data;
      renderPageMeta();
      renderStatusBar();
      renderTopDown();
    } catch (err) {
      showError(err.message || String(err));
    }
  }

  init();
})();
