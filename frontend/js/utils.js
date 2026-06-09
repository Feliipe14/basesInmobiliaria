/* ─── Utilidades ─────────────────────────────────────────────────────────── */

function adjustK(rangeId, valId, delta) {
  const el = document.getElementById(rangeId);
  el.value = Math.min(el.max, Math.max(el.min, +el.value + delta));
  document.getElementById(valId).textContent = el.value;
}

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

function showError(containerId, msg) {
  const el = document.getElementById(containerId);
  if (el) el.innerHTML = '<div class="flex items-start gap-3 p-4 rounded-lg border" style="background:rgba(239,68,68,0.08);border-color:rgba(239,68,68,0.25)"><span class="text-2xl">⚠️</span><div><div class="text-sm font-semibold text-red-400 mb-1">Error</div><div class="text-sm text-red-300">' + escHtml(msg) + '</div></div></div>';
}

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

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function strategyBadge(s) {
  var map = {fixed_size:'badge-fs', sentence:'badge-sn', semantic:'badge-sm'};
  return '<span class="badge ' + (map[s]||'badge-tipo') + '">' + escHtml(s) + '</span>';
}

function scoreClass(v) {
  if (v >= 0.75) return 'score-ex';
  if (v >= 0.60) return 'score-good';
  if (v >= 0.45) return 'score-mod';
  return 'score-low';
}

function scoreBarFill(v) {
  var pct = Math.round(v*100);
  var color;
  if (v >= 0.75) color = '#10b981';
  else if (v >= 0.60) color = '#3b82f6';
  else if (v >= 0.45) color = '#f59e0b';
  else color = '#64748b';
  return '<div class="score-bar-wrap" style="width:100%"><div class="score-bar-fill" style="width:' + pct + '%;background:' + color + '"></div></div>';
}

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

function createSkeletonLoader(n, h) {
  h = h || 'h-24';
  var out = '';
  for (var i = 0; i < n; i++) out += '<div class="skeleton ' + h + ' mb-3"></div>';
  return out;
}

function copyText(t) {
  navigator.clipboard.writeText(t).then(function () {
    showToast('Copiado al portapapeles','success');
  });
}

// SVG icono de edificio para placeholders de imágenes
function buildingIcon(size) {
  size = size || 48;
  return '<svg width="' + size + '" height="' + size + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3"><rect x="4" y="2" width="16" height="20" rx="1"/><line x1="9" y1="6" x2="9" y2="10"/><line x1="15" y1="6" x2="15" y2="10"/><line x1="9" y1="14" x2="9" y2="18"/><line x1="15" y1="14" x2="15" y2="18"/><line x1="4" y1="10" x2="20" y2="10"/></svg>';
}
