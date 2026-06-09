/* ─── Utilidades ─────────────────────────────────────────────────────────── */

// Ajusta el valor de un slider numerico, usado para seleccionar top_k.
// Recibe el id del rango y el id del label; delta indica si suma o resta.
// Concepto clave: **control deslizante** y **parametro K**.
function adjustK(rangeId, valId, delta) {
  const el = document.getElementById(rangeId);
  el.value = Math.min(el.max, Math.max(el.min, +el.value + delta));
  document.getElementById(valId).textContent = el.value;
}

// Muestra un mensaje flotante (toast) en la parte inferior de la pantalla.
// type puede ser 'info', 'success' o 'error' para cambiar el color.
// Concepto clave: **notificacion toast** y **feedback visual**.
function showToast(msg, type) {
  type = type || 'info';
  const c = document.getElementById('toast-container');
  const t = document.createElement('div');
  t.className = 'toast toast-' + type;
  t.textContent = msg;
  c.appendChild(t);
  requestAnimationFrame(function () {
    requestAnimationFrame(function () { t.classList.add('show'); });
  });
  setTimeout(function () {
    t.classList.remove('show');
    setTimeout(function () { t.remove(); }, 350);
  }, 3000);
}

// Muestra un bloque de error estilizado dentro de un contenedor.
// Escapa HTML para evitar inyeccion de codigo.
// Concepto clave: **manejo de errores** y **escape de HTML**.
function showError(containerId, msg) {
  const el = document.getElementById(containerId);
  if (el) el.innerHTML = '<div class="flex items-start gap-3 p-4 rounded-lg border" style="background:rgba(239,68,68,0.08);border-color:rgba(239,68,68,0.25)"><span class="text-2xl">⚠️</span><div><div class="text-sm font-semibold text-red-400 mb-1">Error</div><div class="text-sm text-red-300">' + escHtml(msg) + '</div></div></div>';
}

// Activa o desactiva el estado de carga en un boton.
// Cuando loading=true, deshabilita el boton y muestra un spinner.
// Concepto clave: **estado de carga** y **spinner**.
function setLoading(btnId, loading) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  if (loading) {
    btn._orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Cargando...';
  } else {
    btn.disabled = false;
    btn.innerHTML = btn._orig || btn.innerHTML;
  }
}

// Escapa caracteres especiales HTML para evitar XSS al insertar texto.
// Convierte &, <, > y " en sus entidades HTML seguras.
// Concepto clave: **seguridad XSS** y **escape de caracteres**.
function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Devuelve HTML de una insignia (badge) segun la estrategia de chunking.
// Mapea fixed_size, sentence y semantic a clases CSS de colores distintos.
// Concepto clave: **insignia de estrategia** y **etiqueta visual**.
function strategyBadge(s) {
  var map = {fixed_size:'badge-fs', sentence:'badge-sn', semantic:'badge-sm'};
  return '<span class="badge ' + (map[s]||'badge-tipo') + '">' + escHtml(s) + '</span>';
}

// Asigna una clase de color segun el score de relevancia (0 a 1).
// Rangos: excelente >= 0.75, bueno >= 0.60, moderado >= 0.45, bajo < 0.45.
// Concepto clave: **score de relevancia** y **codigo de colores**.
function scoreClass(v) {
  if (v >= 0.75) return 'score-ex';
  if (v >= 0.60) return 'score-good';
  if (v >= 0.45) return 'score-mod';
  return 'score-low';
}

// Genera una barra de progreso visual para mostrar el score.
// El color de la barra cambia segun el valor (verde, azul, amarillo, gris).
// Concepto clave: **barra de progreso** y **visualizacion de score**.
function scoreBarFill(v) {
  var pct = Math.round(v*100);
  var color;
  if (v >= 0.75) color = '#10b981';
  else if (v >= 0.60) color = '#3b82f6';
  else if (v >= 0.45) color = '#f59e0b';
  else color = '#64748b';
  return '<div class="score-bar-wrap" style="width:100%"><div class="score-bar-fill" style="width:' + pct + '%;background:' + color + '"></div></div>';
}

// Construye una tarjeta HTML que muestra un chunk de texto recuperado.
// Incluye score, estrategia de chunking, tipo de documento y el texto truncado.
// Concepto clave: **tarjeta de chunk** y **resultado de busqueda**.
function createChunkCard(chunk) {
  var text = escHtml(chunk.texto || '');
  var short = text.length > 300;
  var id = 'cc-' + (Math.random().toString(36).slice(2));
  return '<div class="chunk-card">' +
    '<div class="flex flex-wrap items-center gap-2 mb-2">' +
      '<span class="score-badge ' + scoreClass(chunk.score) + '">' + chunk.score.toFixed(4) + '</span>' +
      strategyBadge(chunk.estrategia_chunking) +
      (chunk.tipo_doc ? '<span class="badge badge-tipo">' + escHtml(chunk.tipo_doc) + '</span>' : '') +
    '</div>' +
    '<div id="' + id + '" class="chunk-text">' + (short ? text.slice(0,300)+'…' : text) + '</div>' +
    (short ? '<span class="chunk-more" onclick="expandChunk(\'' + id + '\',this,\'' + escHtml(text).replace(/'/g,"&#39;") + '\')">Ver más…</span>' : '') +
    '<div class="flex flex-wrap gap-3 mt-2 pt-2" style="border-top:1px solid var(--border)">' +
      '<span class="text-xs text-text-muted font-mono">' + escHtml(chunk.doc_id||'') + '</span>' +
      '<span class="text-xs text-text-muted font-mono">' + escHtml(chunk.chunk_id||'') + '</span>' +
    '</div>' +
  '</div>';
}

// Expande o colapsa el texto completo de un chunk dentro de su tarjeta.
// Alterna entre mostrar 300 caracteres y el texto completo.
// Concepto clave: **texto expandible** y **toggle de lectura**.
function expandChunk(id, btn, fullText) {
  var el = document.getElementById(id);
  if (btn.textContent === 'Ver más…') {
    el.innerHTML = fullText;
    el.classList.add('expanded');
    btn.textContent = 'Ver menos';
  } else {
    el.innerHTML = fullText.slice(0,300)+'…';
    el.classList.remove('expanded');
    btn.textContent = 'Ver más…';
  }
}

// Genera n esqueletos de carga (skeleton loaders) para mostrar mientras se espera la API.
// Cada skeleton tiene una altura personalizable, por defecto h-24.
// Concepto clave: **skeleton loader** y **experiencia de carga**.
function createSkeletonLoader(n, h) {
  h = h || 'h-24';
  var out = '';
  for (var i = 0; i < n; i++) out += '<div class="skeleton ' + h + ' mb-3"></div>';
  return out;
}

// Copia un texto al portapapeles del usuario usando la API del navegador.
// Muestra un toast de confirmacion si la operacion es exitosa.
// Concepto clave: **portapapeles** y **clipboard API**.
function copyText(t) {
  navigator.clipboard.writeText(t).then(function () {
    showToast('Copiado al portapapeles','success');
  });
}

// SVG icono de edificio para placeholders de imagenes.
// Se usa como fallback visual cuando la imagen real no carga.
// Concepto clave: **SVG inline** y **placeholder visual**.
function buildingIcon(size) {
  size = size || 48;
  return '<svg width="' + size + '" height="' + size + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3"><rect x="4" y="2" width="16" height="20" rx="1"/><line x1="9" y1="6" x2="9" y2="10"/><line x1="15" y1="6" x2="15" y2="10"/><line x1="9" y1="14" x2="9" y2="18"/><line x1="15" y1="14" x2="15" y2="18"/><line x1="4" y1="10" x2="20" y2="10"/></svg>';
}
