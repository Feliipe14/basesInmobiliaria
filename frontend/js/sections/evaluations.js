/* ─── Evaluaciones ──────────────────────────────────────────────────────── */

// Renderiza una barra coloreada para métricas RAGAS (verde / amarillo / rojo).
function ragasBar(value) {
  if (value == null) return '<span class="text-text-muted">—</span>';
  var pct = Math.round(value * 100);
  var color = pct >= 75 ? '#22c55e' : pct >= 50 ? '#eab308' : '#ef4444';
  return (
    '<div class="flex items-center gap-1.5">' +
    '<div style="width:48px;height:6px;background:#e5e7eb;border-radius:3px;overflow:hidden">' +
    '<div style="width:' + pct + '%;height:100%;background:' + color + ';border-radius:3px"></div></div>' +
    '<span class="font-mono text-xs">' + value.toFixed(3) + '</span>' +
    '</div>'
  );
}

// Carga la tabla de evaluaciones desde la API (hasta 30 registros).
// Muestra columnas con métricas proxy y RAGAS reales cuando están disponibles.
// Concepto clave: **evaluaciones RAG** y **métricas de calidad RAGAS**.
async function loadEvaluations() {
  var el = document.getElementById('evaluations-table');
  el.innerHTML = createSkeletonLoader(5, 'h-10');
  try {
    var r = await fetch(API + '/evaluations?limit=30');
    if (!r.ok) throw new Error('Error cargando evaluaciones');
    var d = await r.json();
    var evals = d.evaluaciones || [];
    if (!evals.length) {
      el.innerHTML =
        '<div class="callout">No hay evaluaciones guardadas aún. ' +
        'Ejecuta el experimento o haz clic en <strong>Ejecutar Evaluación RAGAS</strong>.</div>';
      return;
    }

    var hasRagas = evals.some(function (e) { return e.faithfulness != null; });

    var thead =
      '<tr>' +
      '<th>ID</th>' +
      '<th>Pregunta / Query ID</th>' +
      '<th>Estrategia</th>' +
      '<th>Relevancia</th>' +
      '<th>Precisión</th>' +
      '<th title="RAGAS: ¿respuesta fundamentada en el contexto?">Faithfulness ⭐</th>' +
      '<th title="RAGAS: ¿respuesta relevante para la pregunta?">Ans. Relevancy ⭐</th>' +
      '<th title="RAGAS: ¿contexto contiene la respuesta esperada?">Context Recall ⭐</th>' +
      '<th>Modelo Eval</th>' +
      '<th>Fecha</th>' +
      '</tr>';

    var tbody = evals.map(function (e) {
      var label = e.question
        ? escHtml(e.question.slice(0, 45)) + (e.question.length > 45 ? '…' : '')
        : '<span class="font-mono text-xs text-text-muted">' + escHtml((e.rag_query_id || '').slice(-12)) + '</span>';
      var isRagas = (e.modelo_eval || '').startsWith('ragas-');
      return (
        '<tr class="' + (isRagas ? 'bg-green-50/30' : '') + '">' +
        '<td class="font-mono text-xs text-text-muted">' + escHtml((e._id || '').slice(-10)) + '</td>' +
        '<td class="text-xs max-w-xs">' + label + '</td>' +
        '<td class="text-xs">' + escHtml(e.estrategia_chunking || '—') + '</td>' +
        '<td><div class="flex items-center gap-2">' + scoreBarFill(e.relevancia || 0) +
          '<span class="font-mono text-xs">' + (e.relevancia || 0).toFixed(3) + '</span></div></td>' +
        '<td><div class="flex items-center gap-2">' + scoreBarFill(e.precision || 0) +
          '<span class="font-mono text-xs">' + (e.precision || 0).toFixed(3) + '</span></div></td>' +
        '<td>' + ragasBar(e.faithfulness) + '</td>' +
        '<td>' + ragasBar(e.answer_relevancy) + '</td>' +
        '<td>' + ragasBar(e.context_recall) + '</td>' +
        '<td class="text-xs">' + escHtml(e.modelo_eval || '') + '</td>' +
        '<td class="text-xs text-text-muted">' + (e.fecha ? new Date(e.fecha).toLocaleDateString('es-CO') : '—') + '</td>' +
        '</tr>'
      );
    }).join('');

    var footer =
      '<div class="text-xs text-text-muted mt-2">' + evals.length + ' evaluaciones cargadas' +
      (hasRagas
        ? ' · <span class="text-green-600 font-medium">✓ Evaluaciones RAGAS reales disponibles</span> (filas en verde)'
        : ' · Las columnas ⭐ requieren ejecutar la evaluación RAGAS') +
      '</div>';

    el.innerHTML =
      '<div class="overflow-x-auto"><table class="data-table"><thead>' +
      thead + '</thead><tbody>' + tbody + '</tbody></table></div>' + footer;

  } catch (e) {
    showError('evaluations-table', e.message);
  }
}

// Ejecuta la evaluación RAGAS completa llamando al endpoint POST /evaluations/run-ragas.
// Muestra progreso al usuario y recarga la tabla al terminar.
// Concepto clave: **evaluación RAGAS en tiempo real** con LLM como juez.
async function runRagasEvaluation() {
  var btn = document.getElementById('btn-run-ragas');
  var statusEl = document.getElementById('ragas-run-status');
  if (!btn || !statusEl) return;

  btn.disabled = true;
  btn.innerHTML =
    '<svg class="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
    '<path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg> Evaluando… (puede tardar 5-10 min)';
  statusEl.innerHTML =
    '<div class="callout mt-2 text-xs">' +
    '⏳ Evaluación RAGAS en progreso. Se están procesando 22 preguntas × 3 estrategias con Groq como LLM juez. ' +
    'No cierres esta pestaña.</div>';

  try {
    var r = await fetch(API + '/evaluations/run-ragas', { method: 'POST' });
    var data = await r.json();

    if (!r.ok) {
      throw new Error(data.detail || 'Error al ejecutar RAGAS');
    }

    // Build summary HTML
    var resumen = data.resumen || {};
    var rows = Object.entries(resumen).map(function (entry) {
      var strat = entry[0], scores = entry[1];
      if (scores.error) {
        return '<tr><td>' + escHtml(strat) + '</td><td colspan="3" class="text-red-500 text-xs">' + escHtml(scores.error) + '</td></tr>';
      }
      return (
        '<tr>' +
        '<td class="font-medium">' + escHtml(strat) + '</td>' +
        '<td>' + ragasBar(scores.faithfulness) + '</td>' +
        '<td>' + ragasBar(scores.answer_relevancy) + '</td>' +
        '<td>' + ragasBar(scores.context_recall) + '</td>' +
        '</tr>'
      );
    }).join('');

    statusEl.innerHTML =
      '<div class="callout mt-2">' +
      '<p class="font-medium text-green-700 mb-2">✅ Evaluación RAGAS completada</p>' +
      '<table class="data-table text-xs"><thead><tr>' +
      '<th>Estrategia</th><th>Faithfulness</th><th>Answer Relevancy</th><th>Context Recall</th>' +
      '</tr></thead><tbody>' + rows + '</tbody></table></div>';

    showToast('Evaluación RAGAS completada', 'success');
    await loadEvaluations();

  } catch (e) {
    statusEl.innerHTML =
      '<div class="callout mt-2 text-red-600 text-xs">❌ Error: ' + escHtml(e.message) + '</div>';
    showToast('Error en evaluación RAGAS', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML =
      '<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
      '<polygon points="5 3 19 12 5 21 5 3"/></svg> Ejecutar Evaluación RAGAS';
  }
}

// Copia el código de RAGAS al portapapeles.
// Concepto clave: **copiar código** y **evaluación RAGAS**.
function copyRagasCode() {
  var code = document.getElementById('ragas-code').textContent;
  navigator.clipboard.writeText(code).then(function () {
    showToast('Código copiado', 'success');
    document.getElementById('btn-copy-ragas').innerHTML = '✓ Copiado';
    setTimeout(function () {
      document.getElementById('btn-copy-ragas').innerHTML =
        '<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
        '<rect x="9" y="9" width="13" height="13" rx="2"/>' +
        '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copiar código';
    }, 2000);
  });
}
