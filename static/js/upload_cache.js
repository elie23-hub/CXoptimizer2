/**
 * Keep the uploaded survey file in IndexedDB so Vercel/serverless can rehydrate /tmp.
 */
(function () {
  var DB_NAME = "gapAnalyzerUpload";
  var STORE = "files";
  var KEY = "current";

  function openDb() {
    return new Promise(function (resolve, reject) {
      if (!window.indexedDB) {
        reject(new Error("IndexedDB unavailable"));
        return;
      }
      var req = indexedDB.open(DB_NAME, 1);
      req.onerror = function () {
        reject(req.error);
      };
      req.onupgradeneeded = function (e) {
        e.target.result.createObjectStore(STORE);
      };
      req.onsuccess = function () {
        resolve(req.result);
      };
    });
  }

  async function save(file) {
    if (!file) return;
    var db = await openDb();
    await new Promise(function (resolve, reject) {
      var tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).put(
        { filename: file.name, blob: file, savedAt: Date.now() },
        KEY
      );
      tx.oncomplete = function () {
        resolve();
      };
      tx.onerror = function () {
        reject(tx.error);
      };
    });
  }

  async function get() {
    var db = await openDb();
    return new Promise(function (resolve, reject) {
      var tx = db.transaction(STORE, "readonly");
      var req = tx.objectStore(STORE).get(KEY);
      req.onsuccess = function () {
        resolve(req.result || null);
      };
      req.onerror = function () {
        reject(req.error);
      };
    });
  }

  async function clear() {
    try {
      var db = await openDb();
      await new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE, "readwrite");
        tx.objectStore(STORE).delete(KEY);
        tx.oncomplete = function () {
          resolve();
        };
        tx.onerror = function () {
          reject(tx.error);
        };
      });
    } catch (e) {}
  }

  async function serverHasUpload() {
    try {
      var res = await fetch("/api/session/status");
      var data = await res.json();
      return !!(data && data.ok && data.has_upload);
    } catch (e) {
      return false;
    }
  }

  async function restoreServer() {
    var entry = await get();
    if (!entry || !entry.blob) return false;
    var fd = new FormData();
    fd.append("survey_file", entry.blob, entry.filename || "upload.sav");
    var res = await fetch("/api/session/restore", { method: "POST", body: fd });
    var data = await res.json();
    return !!(data && data.ok);
  }

  async function ensureServerUpload() {
    if (await serverHasUpload()) return true;
    return restoreServer();
  }

  window.gapAnalyzerUploadCache = {
    save: save,
    get: get,
    clear: clear,
    ensureServerUpload: ensureServerUpload,
  };
})();
