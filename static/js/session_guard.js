/**
 * Treat leftover Flask/disk uploads as absent unless this tab actually
 * uploaded a file (sessionStorage set by upload.js).
 */
(function () {
  var UPLOAD_KEY = "gapAnalyzer_upload_session";
  var GAP_KEY = "gapAnalyzer_gap_session";
  var SIM_KEY = "gapAnalyzer_sim_summary";

  function hasClientUpload() {
    try {
      var data = JSON.parse(sessionStorage.getItem(UPLOAD_KEY) || "null");
      return !!(data && data.html);
    } catch (e) {
      return false;
    }
  }

  function clearClientAnalysis() {
    try {
      sessionStorage.removeItem(GAP_KEY);
      sessionStorage.removeItem(SIM_KEY);
    } catch (e) {}
  }

  function hideStaleFileBadge() {
    var badge = document.querySelector(".file-badge");
    if (badge) badge.remove();
  }

  window.gapAnalyzerHasUpload = hasClientUpload();

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
