/**
 * Client session gate — upload tab only unlocks Gap / Simulation / Summary.
 * Works the same locally and on Vercel (sessionStorage + IndexedDB).
 */
(function () {
  var UPLOAD_KEY = "gapAnalyzer_upload_session";
  var STORAGE_KEYS = [
    UPLOAD_KEY,
    "gapAnalyzer_gap_session",
    "gapAnalyzer_gap_meta",
    "gapAnalyzer_sim_snapshot",
    "gapAnalyzer_sim_meta",
    "gapAnalyzer_sim_summary",
  ];

  var ANALYSIS_PATH = /\/(?:gap-analysis|simulation|summary)\/?$/;

  function isPageReload() {
    try {
      var nav = performance.getEntriesByType("navigation")[0];
      return !nav || nav.type === "reload";
    } catch (e) {
      return false;
    }
  }

  function isUploadPage() {
    return /\/upload\/?$/.test(window.location.pathname);
  }

  function hasClientUpload() {
    try {
      var data = JSON.parse(sessionStorage.getItem(UPLOAD_KEY) || "null");
      return !!(data && data.html);
    } catch (e) {
      return false;
    }
  }

  function clearAllClientState() {
    STORAGE_KEYS.forEach(function (key) {
      try {
        sessionStorage.removeItem(key);
      } catch (e) {}
    });
    if (window.gapAnalyzerUploadCache) {
      window.gapAnalyzerUploadCache.clear();
    }
    var badge = document.querySelector(".file-badge");
    if (badge) badge.remove();
  }

  function resetServerSession() {
    return fetch("/api/session/reset", { method: "POST" }).catch(function () {});
  }

  function applyNavGuard() {
    var allowed = hasClientUpload();
    document.querySelectorAll(".app-nav-link").forEach(function (link) {
      var href = link.getAttribute("href") || "";
      var isAnalysis =
        href.indexOf("gap-analysis") !== -1 ||
        href.indexOf("simulation") !== -1 ||
        href.indexOf("summary") !== -1;
      if (!isAnalysis) return;
      link.classList.toggle("is-disabled", !allowed);
      if (!allowed) {
        link.setAttribute("aria-disabled", "true");
        link.setAttribute("tabindex", "-1");
      } else {
        link.removeAttribute("aria-disabled");
        link.removeAttribute("tabindex");
      }
    });
  }

  function bindNavGuard() {
    document.querySelectorAll(".app-nav-link").forEach(function (link) {
      if (link.dataset.gapGuardBound === "1") return;
      link.dataset.gapGuardBound = "1";
      link.addEventListener("click", function (e) {
        var href = link.getAttribute("href") || "";
        var isAnalysis =
          href.indexOf("gap-analysis") !== -1 ||
          href.indexOf("simulation") !== -1 ||
          href.indexOf("summary") !== -1;
        if (isAnalysis && !hasClientUpload()) {
          e.preventDefault();
        }
      });
    });
  }

  function guardAnalysisRoute() {
    if (hasClientUpload()) return;
    if (ANALYSIS_PATH.test(window.location.pathname)) {
      window.location.replace("/upload");
    }
  }

  /* Upload page reload => fresh start (no stale gap/sim data). */
  if (isPageReload() && isUploadPage()) {
    clearAllClientState();
    resetServerSession();
  }

  window.gapAnalyzerClearAllClientState = clearAllClientState;
  window.gapAnalyzerHasUpload = hasClientUpload();
  window.gapAnalyzerRefreshNavGuard = function () {
    window.gapAnalyzerHasUpload = hasClientUpload();
    applyNavGuard();
  };

  guardAnalysisRoute();
  applyNavGuard();
  bindNavGuard();

  window.gapAnalyzerSessionReady = (async function () {
    if (hasClientUpload()) return true;
    await resetServerSession();
    return false;
  })();
})();
