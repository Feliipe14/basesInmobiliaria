/* ─── Pipeline RAG ──────────────────────────────────────────────────────── */

// Genera los botones de consultas rapidas para RAG a partir del arreglo QUERIES.
// Cada boton al hacer clic llena el campo de texto con la pregunta.
// Concepto clave: **consultas rapidas** y **preguntas predefinidas**.
function buildRagQuickBtns() {
  var c = document.getElementById('rag-quick-btns');
  c.innerHTML = QUERIES.map(function (q) {
    return '<button class="btn-query" onclick="fillRagQuery(\'' + q.replace(/'/g,"\\'") + '\',this)">' + escHtml(q) + '</button>';
  }).join('');
}

// Llena el campo de consulta RAG con una pregunta y resalta el boton seleccionado.
// Concepto clave: **seleccion de consulta** y **pregunta predefinida**.
function fillRagQuery(q, btn) {
  document.getElementById('rag-query').value = q;
  document.querySelectorAll('#rag-quick-btns .btn-query').forEach(function (b) { b.classList.remove('selected'); });
  btn.classList.add('selected');
}

// Resalta el boton de consulta cuyo texto coincida con la pregunta actual.
// Se usa cuando se navega desde el dashboard para que el boton quede seleccionado.
// Concepto clave: **sincronizacion visual** y **resaltado de boton**.
function highlightRagBtn(q) {
  document.querySelectorAll('#rag-quick-btns .btn-query').forEach(function (b) {
    b.classList.toggle('selected', b.textContent === q);
  });
}

// Ejecuta el pipeline completo de RAG: recupera chunks relevantes y genera respuesta con el LLM.
// Muestra una barra de progreso con 3 pasos: consulta, recuperacion y generacion.
// Presenta la respuesta final junto con los chunks utilizados como contexto.
// Concepto clave: **pipeline RAG** y **generacion aumentada por recuperacion**.
async function doRag() {
  var query = document.getElementById('rag-query').value.trim();
  if (!query) { showToast('Ingresa una pregunta','error'); return; }
  var strategy = document.getElementById('rag-strategy').value;
  var topK = +document.getElementById('rag-k').value;

  setLoading('btn-rag', true);
  document.getElementById('rag-loading').classList.remove('hidden');
  document.getElementById('rag-result').innerHTML = '';
  var steps = ['rag-step-1','rag-step-2','rag-step-3'];
  steps.forEach(function (s) { document.getElementById(s).className = 'progress-step waiting'; });
  document.getElementById('rag-progress-bar').style.width = '0%';

  function activate(idx, delay) {
    delay = delay || 400;
    return new Promise(function (resolve) {
      setTimeout(function () {
        document.getElementById(steps[idx]).className = 'progress-step active';
        document.getElementById('rag-progress-bar').style.width = ((idx+1)*33) + '%';
        if (idx>0) document.getElementById(steps[idx-1]).className = 'progress-step done';
        resolve();
      }, delay);
    });
  }
  activate(0, 50);
  activate(1, 500);

  try {
    var r = await fetch(API + '/rag', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({query:query, strategy:strategy, top_k:topK}),
    });
    var d = await r.json();
    if (!r.ok) throw new Error(d.detail||'Error en RAG');

    await activate(2, 0);
    await new Promise(function (r) { setTimeout(r, 300); });
    steps.forEach(function (s) { document.getElementById(s).className = 'progress-step done'; });
    document.getElementById('rag-progress-bar').style.width = '100%';

    await new Promise(function (r) { setTimeout(r, 300); });
    document.getElementById('rag-loading').classList.add('hidden');

    var chunksHtml = (d.chunks_usados||[]).map(function (c) {
      return '<div class="flex items-start gap-2 p-2 rounded bg-bg-base text-xs">' +
        '<span class="score-badge ' + scoreClass(c.score) + ' flex-shrink-0">' + c.score.toFixed(3) + '</span>' +
        '<span class="text-text-muted line-clamp-2">' + escHtml((c.texto||'').slice(0,120)) + '…</span>' +
      '</div>';
    }).join('');

    document.getElementById('rag-result').innerHTML =
      '<div class="card overflow-hidden">' +
        '<div class="px-5 py-3 flex items-center gap-2" style="background:linear-gradient(90deg,rgba(59,130,246,0.15),rgba(6,182,212,0.08))">' +
          '<svg class="w-5 h-5 text-accent-blue flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v18m0 0h10a2 2 0 0 0 2-2v-4M9 21H5a2 2 0 0 1-2-2v-4m0 0h18"/></svg>' +
          '<span class="font-semibold text-text-main text-sm">Respuesta del Sistema RAG</span>' +
        '</div>' +
        '<div class="p-5">' +
          '<div class="text-[15px] leading-relaxed text-text-main mb-4" style="white-space:pre-wrap">' + escHtml(d.respuesta) + '</div>' +
          '<div class="flex flex-wrap gap-3 text-xs text-text-muted pt-3" style="border-top:1px solid var(--border)">' +
            '<span class="font-mono">⏱ ' + d.tiempo_respuesta_ms + 'ms</span>' +
            '<span>' + escHtml(d.modelo_llm) + '</span>' +
            strategyBadge(d.estrategia_chunking) +
            '<span class="font-mono text-text-muted">' + escHtml(d.log_id) + '</span>' +
            '<button onclick="copyText(\'' + escHtml(d.respuesta).replace(/'/g,"&#39;") + '\')" class="ml-auto text-accent-blue hover:underline flex items-center gap-1">' +
              '<svg class="w-3 h-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>' +
              ' Copiar' +
            '</button>' +
          '</div>' +
        '</div>' +
      '</div>' +
      '<details class="card mt-3">' +
        '<summary class="p-4 cursor-pointer text-sm font-semibold text-text-muted select-none hover:text-text-main">' +
          'Ver contexto utilizado (' + (d.chunks_usados||[]).length + ' chunks)' +
        '</summary>' +
        '<div class="px-4 pb-4 space-y-2">' + chunksHtml + '</div>' +
      '</details>';
  } catch(e) {
    document.getElementById('rag-loading').classList.add('hidden');
    showError('rag-result', e.message);
  } finally {
    setLoading('btn-rag', false);
  }
}
