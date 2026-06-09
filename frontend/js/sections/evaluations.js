/* ─── Evaluaciones ──────────────────────────────────────────────────────── */

async function loadEvaluations() {
  var el = document.getElementById('evaluations-table');
  el.innerHTML = createSkeletonLoader(5,'h-10');
  try {
    var r = await fetch(API + '/evaluations?limit=30');
    if (!r.ok) throw new Error('Error cargando evaluaciones');
    var d = await r.json();
    var evals = d.evaluaciones || [];
    if (!evals.length) {
      el.innerHTML = '<div class="callout">No hay evaluaciones guardadas aún. Ejecuta el experimento primero.</div>';
      return;
    }
    var thead = '<tr><th>ID</th><th>Query ID</th><th>Relevancia</th><th>Precisión</th><th>Faithfulness</th><th>Ans. Relevancy</th><th>Context Recall</th><th>Modelo</th><th>Fecha</th></tr>';
    var tbody = evals.map(function (e) {
      return '<tr>' +
        '<td class="font-mono text-xs text-text-muted">' + escHtml((e._id||'').slice(-8)) + '</td>' +
        '<td class="font-mono text-xs">' + escHtml((e.rag_query_id||'').slice(-12)) + '</td>' +
        '<td><div class="flex items-center gap-2">' + scoreBarFill(e.relevancia||0) + '<span class="font-mono text-xs">' + (e.relevancia||0).toFixed(3) + '</span></div></td>' +
        '<td><div class="flex items-center gap-2">' + scoreBarFill(e.precision||0) + '<span class="font-mono text-xs">' + (e.precision||0).toFixed(3) + '</span></div></td>' +
        '<td class="text-text-muted text-xs">' + (e.faithfulness != null ? (e.faithfulness).toFixed(3) : '—') + '</td>' +
        '<td class="text-text-muted text-xs">' + (e.answer_relevancy != null ? (e.answer_relevancy).toFixed(3) : '—') + '</td>' +
        '<td class="text-text-muted text-xs">' + (e.context_recall != null ? (e.context_recall).toFixed(3) : '—') + '</td>' +
        '<td class="text-xs">' + escHtml(e.modelo_eval||'') + '</td>' +
        '<td class="text-xs text-text-muted">' + (e.fecha ? new Date(e.fecha).toLocaleDateString('es-CO') : '—') + '</td>' +
      '</tr>';
    }).join('');
    el.innerHTML = '<div class="overflow-x-auto"><table class="data-table"><thead>' + thead + '</thead><tbody>' + tbody + '</tbody></table></div>' +
      '<div class="text-xs text-text-muted mt-2">' + evals.length + ' evaluaciones cargadas · Las columnas Faithfulness, Answer Relevancy y Context Recall requieren evaluación RAGAS completa con LLM como juez.</div>';
  } catch(e) {
    showError('evaluations-table', e.message);
  }
}

function copyRagasCode() {
  var code = document.getElementById('ragas-code').textContent;
  navigator.clipboard.writeText(code).then(function () {
    showToast('Código copiado','success');
    document.getElementById('btn-copy-ragas').innerHTML = '✓ Copiado';
    setTimeout(function () {
      document.getElementById('btn-copy-ragas').innerHTML = '<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copiar código';
    }, 2000);
  });
}
