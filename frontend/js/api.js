/* ─── Llamadas a la API ─────────────────────────────────────────────────── */

async function checkApi() {
  try {
    var r = await fetch(API + '/');
    if (r.ok) {
      document.getElementById('api-dot').className = 'pulse-dot pulse-online';
      document.getElementById('api-text').textContent = 'API Conectada';
      document.getElementById('offline-banner').style.display = 'none';
      return true;
    }
  } catch(e) {}
  document.getElementById('api-dot').className = 'pulse-dot pulse-offline';
  document.getElementById('api-text').textContent = 'API Desconectada';
  document.getElementById('offline-banner').style.display = 'block';
  return false;
}
