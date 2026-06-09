/* ─── Init ───────────────────────────────────────────────────────────────── */

(function init() {
  buildRagQuickBtns();
  buildCompareQuick();
  checkApi().then(function () {
    loadDashboard();
  });
  setInterval(checkApi, 30000);
})();
