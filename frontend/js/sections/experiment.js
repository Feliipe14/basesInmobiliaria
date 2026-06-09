/* ─── Experimento de Chunking ───────────────────────────────────────────── */

var _expData = null;
var _expSortDir = 1;
var _expSortKey = 'score_promedio';

// Ejecuta el experimento completo que prueba las tres estrategias de chunking contra todas las consultas.
// Obtiene resultados desde la API y los almacena en _expData para ordenamiento y filtros.
// Concepto clave: **experimento de chunking** y **evaluacion comparativa**.
async function doExperiment() {
  var topK = document.getElementById('exp-k').value;
  setLoading('btn-experiment',true);
  document.getElementById('exp-loading').classList.remove('hidden');
  document.getElementById('exp-results').innerHTML = '';

  try {
    var r = await fetch(API + '/experiment/results?top_k=' + topK);
    if (!r.ok) throw new Error('Error ejecutando experimento');
    var d = await r.json();
    _expData = d;
    document.getElementById('exp-loading').classList.add('hidden');
    renderExperiment(d);
  } catch(e) {
    document.getElementById('exp-loading').classList.add('hidden');
    showError('exp-results', e.message);
  } finally {
    setLoading('btn-experiment',false);
  }
}

// Renderiza los resultados del experimento: tarjetas de resumen, tabla comparativa, analisis y mapa de calor.
// Destaca la estrategia optima con una insignia dorada.
// Concepto clave: **visualizacion de resultados** y **rendering de dashboard**.
function renderExperiment(d) {
  var resumen = d.resumen;
  var strats = ['fixed_size','sentence','semantic'];
  var bestStrat = strats.reduce(function(a,b){ return resumen[a].avg_score>resumen[b].avg_score ? a : b; });

  var summaryHtml = strats.map(function (s) {
    var r = resumen[s];
    var isBest = s === bestStrat;
    return '<div class="card p-4' + (isBest?' border-accent-gold':'') + '"' + (isBest?' style="border-color:var(--accent-gold)"':'') + '>' +
      '<div class="flex items-center justify-between mb-2">' +
        strategyBadge(s) +
        (isBest ? '<span class="badge badge-gold">★ ÓPTIMA</span>' : '') +
      '</div>' +
      '<div class="text-3xl font-extrabold font-mono ' + (isBest?'text-accent-gold':'text-text-main') + ' mb-1">' + r.avg_score.toFixed(4) + '</div>' +
      scoreBarFill(r.avg_score) +
      '<div class="mt-3 space-y-1 text-xs text-text-muted">' +
        '<div>Avg chunks: <span class="font-mono text-text-main">' + r.avg_chunks_recuperados + '</span></div>' +
        '<div>Avg longitud: <span class="font-mono text-text-main">' + r.avg_longitud_chars.toFixed(0) + ' chars</span></div>' +
      '</div>' +
    '</div>';
  }).join('');

  var activeStrats = new Set(['fixed_size','sentence','semantic']);
  var tableHtml = buildExpTable(d.resultados, activeStrats);
  var analysisHtml = buildExpAnalysis(resumen, bestStrat);
  var heatmapHtml = buildHeatmap(d.resultados);

  document.getElementById('exp-results').innerHTML =
    '<div class="grid grid-cols-1 md:grid-cols-3 gap-4">' + summaryHtml + '</div>' +

    '<div class="card p-5 mt-5">' +
      '<div class="flex flex-wrap items-center justify-between gap-3 mb-3">' +
        '<h3 class="text-sm font-semibold text-text-main">Tabla Comparativa (30 filas)</h3>' +
        '<div class="flex items-center gap-3 flex-wrap">' +
          '<div class="flex gap-2">' +
            strats.map(function (s) {
              return '<label class="flex items-center gap-1 text-xs cursor-pointer">' +
                '<input type="checkbox" checked data-strat="' + s + '" onchange="filterExpTable(this)" class="accent-blue-500"/> ' + s +
              '</label>';
            }).join('') +
          '</div>' +
          '<button onclick="exportExpCsv()" class="btn-secondary text-xs">' +
            '<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>' +
            ' Exportar CSV' +
          '</button>' +
        '</div>' +
      '</div>' +
      '<div class="overflow-x-auto" id="exp-table-wrap">' + tableHtml + '</div>' +
    '</div>' +

    '<div class="callout-green callout mt-5" id="exp-analysis">' + analysisHtml + '</div>' +

    '<div class="card p-5 mt-5">' +
      '<h3 class="text-sm font-semibold text-text-main mb-3">Mapa de Calor — Score por Consulta y Estrategia</h3>' +
      '<div class="overflow-x-auto">' + heatmapHtml + '</div>' +
    '</div>';
}

// Construye la tabla HTML con los resultados detallados del experimento.
// Soporta filtrado por estrategias activas y marca el ganador de cada consulta.
// Concepto clave: **tabla comparativa** y **filtro de estrategias**.
function buildExpTable(rows, activeStrats) {
  var filtered = rows;
  if (activeStrats) filtered = rows.filter(function (r) { return activeStrats.has(r.estrategia); });
  var queries = [...new Set(rows.map(function (r) { return r.consulta; }))];

  var thead = '<thead><tr>' +
    '<th onclick="sortExpTable(\'consulta\')">Consulta ↕</th>' +
    '<th onclick="sortExpTable(\'estrategia\')">Estrategia ↕</th>' +
    '<th onclick="sortExpTable(\'chunks_recuperados\')">Chunks ↕</th>' +
    '<th onclick="sortExpTable(\'longitud_promedio\')">Avg Long ↕</th>' +
    '<th onclick="sortExpTable(\'score_promedio\')">Score ↕</th>' +
    '<th>Preview</th>' +
  '</tr></thead>';

  var winnerMap = {};
  queries.forEach(function (q) {
    var qRows = rows.filter(function (r) { return r.consulta === q; });
    var winner = qRows.reduce(function (a,b) { return a.score_promedio > b.score_promedio ? a : b; });
    winnerMap[q + '|' + winner.estrategia] = true;
  });

  var tbody = filtered.map(function (row, i) {
    var isWinner = winnerMap[row.consulta + '|' + row.estrategia];
    var isLast = i < filtered.length - 1 && filtered[i+1] && filtered[i+1].consulta !== row.consulta;
    return '<tr class="' + (isWinner?'winner':'') + (isLast?' group-sep':'') + '">' +
      '<td class="text-xs max-w-xs"><span title="' + escHtml(row.consulta) + '">' + escHtml(row.consulta.slice(0,50)) + (row.consulta.length>50?'…':'') + '</span></td>' +
      '<td>' + strategyBadge(row.estrategia) + '</td>' +
      '<td class="font-mono text-xs">' + row.chunks_recuperados + '</td>' +
      '<td class="font-mono text-xs">' + row.longitud_promedio.toFixed(0) + '</td>' +
      '<td><div class="flex items-center gap-2 min-w-[80px]">' + scoreBarFill(row.score_promedio) + '<span class="font-mono text-xs whitespace-nowrap">' + row.score_promedio.toFixed(4) + '</span></div></td>' +
      '<td class="text-xs text-text-muted max-w-xs"><span title="' + escHtml(row.respuesta_preview) + '">' + escHtml((row.respuesta_preview||'').slice(0,80)) + '…</span></td>' +
    '</tr>';
  }).join('');

  return '<table class="data-table" id="exp-table">' + thead + '<tbody>' + tbody + '</tbody></table>';
}

// Ordena la tabla del experimento por una columna, alternando entre ascendente y descendente.
// Modifica el arreglo _expData.resultados y re-renderiza la tabla.
// Concepto clave: **ordenamiento de tabla** y **sort de columnas**.
function sortExpTable(key) {
  if (!_expData) return;
  if (_expSortKey === key) _expSortDir *= -1;
  else { _expSortKey = key; _expSortDir = -1; }
  _expData.resultados.sort(function (a, b) {
    if (a[key] < b[key]) return _expSortDir;
    if (a[key] > b[key]) return -_expSortDir;
    return 0;
  });
  document.getElementById('exp-table-wrap').innerHTML = buildExpTable(_expData.resultados, null);
}

// Filtra las filas de la tabla segun las estrategias seleccionadas con los checkboxes.
// Re-renderiza la tabla mostrando solo las estrategias marcadas.
// Concepto clave: **filtro dinamico** y **checkboxes de estrategia**.
function filterExpTable(cb) {
  if (!_expData) return;
  var checkboxes = document.querySelectorAll('[data-strat]');
  var active = new Set([].slice.call(checkboxes).filter(function (c) { return c.checked; }).map(function (c) { return c.dataset.strat; }));
  document.getElementById('exp-table-wrap').innerHTML = buildExpTable(_expData.resultados, active);
}

// Genera un analisis textual comparativo de las tres estrategias de chunking.
// Explica ventajas y desventajas de cada una y concluye cual es la optima para el dominio inmobiliario.
// Concepto clave: **analisis comparativo** y **conclusion del experimento**.
function buildExpAnalysis(resumen, bestStrat) {
  var strats = ['fixed_size','sentence','semantic'];
  var lines = strats.map(function (s) {
    var r = resumen[s];
    var descs = {
      fixed_size:'Ventaja: predecible y uniforme. Desventaja: puede partir cláusulas contractuales, perdiendo contexto semántico.',
      sentence:'Ventaja: respeta unidades oracionales. Ideal para chats y descripciones. Desventaja: chunks de tamaño variable.',
      semantic:'Ventaja: mayor cohesión temática, mejores scores. Desventaja: más costoso computacionalmente.',
    };
    return '<li class="mb-1"><strong class="text-text-main">' + s + '</strong>: avg score <span class="font-mono text-accent-blue">' + r.avg_score.toFixed(4) + '</span>, avg longitud <span class="font-mono">' + r.avg_longitud_chars.toFixed(0) + '</span> chars. ' + descs[s] + '</li>';
  }).join('');
  var best = resumen[bestStrat];
  return '<strong class="text-green-300 text-sm">📊 ANÁLISIS COMPARATIVO DE ESTRATEGIAS DE CHUNKING</strong>' +
    '<ul class="mt-2 space-y-1 text-xs list-none">' + lines + '</ul>' +
    '<div class="mt-2 text-xs"><strong>CONCLUSIÓN:</strong> Para el dominio inmobiliario colombiano, la estrategia' +
    ' <strong>' + bestStrat.toUpperCase() + '</strong> es la más adecuada con un score promedio de' +
    ' <strong>' + best.avg_score.toFixed(4) + '</strong>.' +
    (bestStrat==='semantic' ? ' La segmentación por similitud semántica preserva mejor el contexto temático de contratos, reglamentos y descripciones de propiedades.' :
      bestStrat==='sentence' ? ' Los límites oracionales capturan unidades informativas naturales del español inmobiliario.' :
      ' La uniformidad del tamaño favorece la consistencia en la recuperación vectorial para este corpus.') + '</div>';
}

// Construye un mapa de calor que muestra el score por consulta y por estrategia.
// Usa colores que van de verde oscuro (alto score) a cafe (bajo score).
// Incluye una escala de referencia al pie de la tabla.
// Concepto clave: **mapa de calor** y **visualizacion de scores**.
function buildHeatmap(rows) {
  var queries = [...new Set(rows.map(function (r) { return r.consulta; }))];
  var strats = ['fixed_size','sentence','semantic'];

  function heatColor(v) {
    if (v >= 0.80) return '#064e3b';
    if (v >= 0.70) return '#065f46';
    if (v >= 0.60) return '#047857';
    if (v >= 0.50) return '#f59e0b';
    if (v >= 0.40) return '#d97706';
    return '#92400e';
  }

  var header = '<tr><th style="text-align:left;padding:6px 10px;font-size:11px;color:var(--text-muted)">Consulta</th>' +
    strats.map(function (s) { return '<th style="padding:6px 10px;font-size:11px;color:var(--text-muted)">' + s + '</th>'; }).join('') + '</tr>';
  var bodyRows = queries.map(function (q) {
    var cells = strats.map(function (s) {
      var row = rows.find(function (r) { return r.consulta === q && r.estrategia === s; });
      var v = row ? row.score_promedio : 0;
      return '<td class="heat-cell" style="background:' + heatColor(v) + ';color:#fff">' + v.toFixed(3) + '</td>';
    }).join('');
    return '<tr><td style="padding:6px 10px;font-size:11px;color:var(--text-muted);max-width:200px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="' + escHtml(q) + '">' + escHtml(q.slice(0,40)) + '…</td>' + cells + '</tr>';
  }).join('');

  var scaleColors = ['#064e3b','#065f46','#047857','#f59e0b','#92400e'];
  var scaleLabels = ['≥0.80','≥0.70','≥0.60','≥0.50','<0.50'];
  var scaleHtml = scaleLabels.map(function (l, i) {
    return '<span class="flex items-center gap-1"><span style="display:inline-block;width:12px;height:12px;background:' + scaleColors[i] + ';border-radius:2px"></span>' + l + '</span>';
  }).join('');

  return '<table style="border-collapse:collapse;width:100%"><thead>' + header + '</thead><tbody>' + bodyRows + '</tbody></table>' +
    '<div class="flex items-center gap-4 mt-2 text-xs text-text-muted"><span>Escala:</span>' + scaleHtml + '</div>';
}

// Exporta los resultados del experimento a un archivo CSV descargable.
// Genera un blob con cabecera y filas, crea un enlace temporal y lo descarga.
// Concepto clave: **exportacion CSV** y **descarga de datos**.
function exportExpCsv() {
  if (!_expData) return;
  var rows = _expData.resultados;
  var header = 'consulta,estrategia,chunks_recuperados,longitud_promedio,score_promedio\n';
  var body = rows.map(function (r) {
    return '"' + r.consulta + '",' + r.estrategia + ',' + r.chunks_recuperados + ',' + r.longitud_promedio.toFixed(1) + ',' + r.score_promedio.toFixed(4);
  }).join('\n');
  var blob = new Blob([header + body], {type:'text/csv;charset=utf-8;'});
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a'); a.href = url; a.download = 'experimento_chunking.csv'; a.click();
  URL.revokeObjectURL(url);
  showToast('CSV exportado','success');
}
