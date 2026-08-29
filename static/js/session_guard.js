/**
 * Treat leftover Flask/disk uploads as absent unless this tab actually
 * uploaded a file (sessionStorage set by upload.js).
 * On serverless (Vercel), keep server session when gap/sim analysis exists in-tab.
 */
(function () {
  var UPLOAD_KEY = "gapAnalyzer_upload_session";
  var GAP_KEY = "gapAnalyzer_gap_session";
  var SIM_SNAPSHOT_KEY = "gapAnalyzer_sim_snapshot";
  var SIM_KEY = "gapAnalyzer_sim_summary";

  function hasClientUpload() {
    try {
      var data = JSON.parse(sessionStorage.getItem(UPLOAD_KEY) || "null");
      return !!(data && data.html);
    } catch (e) {
      return false;
    }
  }

  function hasClientAnalysis() {
    try {
      if (sessionStorage.getItem(GAP_KEY)) return true;
      if (sessionStorage.getItem(SIM_SNAPSHOT_KEY)) return true;
      return false;
    } catch (e) {
      return false;
    }
  }

  function clearClientAnalysis() {
    try {
      sessionStorage.removeItem(GAP_KEY);
      sessionStorage.removeItem(SIM_SNAPSHOT_KEY);
      sessionStorage.removeItem("gapAnalyzer_sim_meta");
      sessionStorage.removeItem("gapAnalyzer_gap_meta");
      sessionStorage.removeItem(SIM_KEY);
    } catch (e) {}
  }

  function hideStaleFileBadge() {
    var badge = document.querySelector(".file-badge");
    if (badge) badge.remove();
  }

  window.gapAnalyzerHasUpload = hasClientUpload() || hasClientAnalysis();

  if (!window.gapAnalyzerHasUpload) {
    hideStaleFileBadge();
    clearClientAnalysis();
  }

  window.gapAnalyzerSessionReady = (async function () {
    if (window.gapAnalyzerHasUpload) return true;
    try {
      await fetch("/api/session/reset", { method: "POST" });
    } catch (e) {}
    return false;
  })();
})();
