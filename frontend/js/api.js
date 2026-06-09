/* ─── Llamadas a la API ─────────────────────────────────────────────────── */

// Verifica si la API de FastAPI esta corriendo en el servidor local.
// Si responde correctamente, muestra un indicador verde "API Conectada".
// Si falla, muestra un banner de "API Desconectada" en rojo.
// Concepto clave: **health check** y **estado del servidor**.
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
