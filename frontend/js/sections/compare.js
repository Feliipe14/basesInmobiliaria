/* ─── Comparar Estrategias de Chunking ──────────────────────────────────── */

// Genera los botones de consultas rapidas para la seccion de comparacion.
// Cada boton al hacer clic llena el campo de consulta y se resalta.
// Concepto clave: **consultas rapidas** y **comparacion de estrategias**.
function buildCompareQuick() {
  var c = document.getElementById('compare-quick');
  c.innerHTML = QUERIES.map(function (q) {
    return '<button class="btn-query" onclick="document.getElementById(\'compare-query\').value=\'' + q.replace(/'/g,"\\'") + '\';document.querySelectorAll(\'#compare-quick .btn-query\').forEach(function(b){b.classList.remove(\'selected\')});this.classList.add(\'selected\')">' + escHtml(q) + '</button>';
  }).join('');
}

// Ejecuta una comparacion lado a lado de las tres estrategias de chunking para una misma consulta.
// Muestra columnas con fixed_size, sentence y semantic, sus metricas y chunks recuperados.
// La estrategia con mejor score promedio se marca como "MEJOR".
// Concepto clave: **comparacion de estrategias** y **analisis de chunking**.
async function doCompare() {
  var query = document.getElementById('compare-query').value.trim();
  if (!query) { showToast('Ingresa una consulta','error'); return; }
  var topK = document.getElementById('compare-k').value;
  var res = document.getElementById('compare-results');

  setLoading('btn-compare',true);
  res.innerHTML = '<div class="grid grid-cols-1 md:grid-cols-3 gap-4 compare-grid">' + createSkeletonLoader(3,'h-80').split('</div>').slice(0,3).map(function (s) { return s+'</div>'; }).join('') + '</div>';

  try {
    var r = await fetch(API + '/chunks/compare?query=' + encodeURIComponent(query) + '&top_k=' + topK);
    if (!r.ok) throw new Error('Error en comparación');
    var d = await r.json();

    var best = d.estrategias.reduce(function (a,b) { return a.score_promedio>b.score_promedio ? a : b; });

    var colHtml = d.estrategias.map(function (s) {
      return '<div class="card p-4">' +
        '<div class="flex items-center justify-between mb-3">' +
          strategyBadge(s.estrategia) +
          (s.estrategia===best.estrategia ? '<span class="badge badge-gold">★ MEJOR</span>' : '') +
        '</div>' +
        '<div class="space-y-2 mb-3">' +
          '<div class="flex justify-between text-xs"><span class="text-text-muted">Total en DB</span><span class="font-mono">' + s.total_chunks_en_db + '</span></div>' +
          '<div class="flex justify-between text-xs"><span class="text-text-muted">Recuperados</span><span class="font-mono">' + s.chunks_recuperados + '</span></div>' +
          '<div class="flex justify-between text-xs"><span class="text-text-muted">Avg longitud</span><span class="font-mono">' + s.longitud_promedio_chars.toFixed(0) + ' chars</span></div>' +
          '<div class="text-xs text-text-muted mb-1">Score promedio</div>' +
          scoreBarFill(s.score_promedio) +
          '<div class="text-right font-mono text-sm font-bold text-text-main">' + s.score_promedio.toFixed(4) + '</div>' +
        '</div>' +
        '<div class="space-y-2 pt-2" style="border-top:1px solid var(--border)">' +
          (s.chunks||[]).map(function (c) {
            return '<div class="p-2 rounded text-xs bg-bg-base" style="border:1px solid var(--border)">' +
              '<span class="score-badge ' + scoreClass(c.score) + ' mr-2">' + c.score.toFixed(3) + '</span>' +
              '<span class="text-text-muted">' + escHtml((c.texto||'').slice(0,150)) + '…</span>' +
            '</div>';
          }).join('') +
        '</div>' +
      '</div>';
    }).join('');

    var analysis = generateCompareAnalysis(d.estrategias, best);

    var tHead = '<tr>' + ['Estrategia','Total DB','Recuperados','Avg Longitud','Score Promedio'].map(function (h) { return '<th>' + h + '</th>'; }).join('') + '</tr>';
    var tRows = d.estrategias.map(function (s) {
      return '<tr class="' + (s.estrategia===best.estrategia?'winner':'') + '">' +
        '<td>' + strategyBadge(s.estrategia) + '</td>' +
        '<td class="font-mono">' + s.total_chunks_en_db + '</td>' +
        '<td class="font-mono">' + s.chunks_recuperados + '</td>' +
        '<td class="font-mono">' + s.longitud_promedio_chars.toFixed(0) + '</td>' +
        '<td><div class="flex items-center gap-2">' + scoreBarFill(s.score_promedio) + '<span class="font-mono text-xs">' + s.score_promedio.toFixed(4) + '</span></div></td>' +
      '</tr>';
    }).join('');

    res.innerHTML =
      '<div class="grid grid-cols-1 md:grid-cols-3 gap-4 compare-grid">' + colHtml + '</div>' +
      '<div class="card p-4 mt-4">' +
        '<div class="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">Tabla comparativa</div>' +
        '<div class="overflow-x-auto"><table class="data-table"><thead>' + tHead + '</thead><tbody>' + tRows + '</tbody></table></div>' +
      '</div>' +
      '<div class="callout mt-4">' + analysis + '</div>';
  } catch(e) {
    showError('compare-results', e.message);
  } finally {
    setLoading('btn-compare',false);
  }
}

// Genera un analisis textual automatico que explica por que la mejor estrategia obtuvo el mayor score.
// Incluye una descripcion personalizada segun la estrategia ganadora.
// Concepto clave: **analisis automatico** y **conclusion de comparacion**.
function generateCompareAnalysis(estrategias, best) {
  var map = {};
  estrategias.forEach(function (s) { map[s.estrategia] = s; });
  return '<strong class="text-blue-300">Análisis Automático:</strong> Para la consulta ingresada, la estrategia' +
    ' <strong>' + best.estrategia + '</strong> obtuvo el mayor score promedio' +
    ' (<strong>' + best.score_promedio.toFixed(4) + '</strong>) con chunks de longitud promedio' +
    ' <strong>' + best.longitud_promedio_chars.toFixed(0) + ' caracteres</strong>.' +
    (best.estrategia==='semantic' ? ' El chunking semántico agrupa oraciones por similitud temática, logrando mayor cohesión conceptual y mejores scores de recuperación.' :
      best.estrategia==='sentence' ? ' El chunking por oraciones preserva unidades lingüísticas completas, lo que favorece la recuperación de información conversacional y descriptiva.' :
      ' El chunking de tamaño fijo garantiza uniformidad y predecibilidad, siendo efectivo cuando los documentos tienen densidad informativa homogénea.');
}
