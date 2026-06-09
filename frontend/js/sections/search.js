/* ─── Búsqueda Semántica ────────────────────────────────────────────────── */

// Ejecuta una busqueda semantica sobre los documentos usando embeddings.
// Envia la consulta con la estrategia de chunking, tipo de documento y top_k.
// Muestra los resultados ordenados por score de similitud coseno.
// Concepto clave: **busqueda semantica** y **similitud de vectores**.
async function doSearch() {
  var query = document.getElementById('search-query').value.trim();
  if (!query) { showToast('Ingresa una consulta primero','error'); return; }
  var strategy = document.getElementById('search-strategy').value;
  var tipo = document.getElementById('search-tipo').value;
  var topK = +document.getElementById('search-k').value;
  var res = document.getElementById('search-results');

  setLoading('btn-search', true);
  res.innerHTML = createSkeletonLoader(5);

  try {
    var t0 = Date.now();
    var r = await fetch(API + '/search', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({query:query, strategy:strategy||undefined, tipo_doc:tipo||undefined, top_k:topK}),
    });
    var d = await r.json();
    if (!r.ok) throw new Error(d.detail||'Error en búsqueda');
    var elapsed = Date.now() - t0;

    var chips = [];
    if (strategy) chips.push('<span class="badge badge-fs">' + escHtml(strategy) + '</span>');
    if (tipo) chips.push('<span class="badge badge-tipo">' + escHtml(tipo) + '</span>');

    res.innerHTML = '<div class="flex items-center justify-between flex-wrap gap-2 mb-3">' +
      '<div class="text-sm font-semibold text-text-main">' + d.total_results + ' resultados</div>' +
      '<div class="flex items-center gap-2">' + chips.join('') + '<span class="text-xs text-text-muted font-mono">' + elapsed + 'ms</span></div>' +
    '</div><div class="space-y-3">' + (d.chunks||[]).map(createChunkCard).join('') + '</div>';
  } catch(e) {
    showError('search-results', e.message);
  } finally {
    setLoading('btn-search', false);
  }
}

// Limpia el formulario de busqueda: vacia campos, restablece valores por defecto y borra resultados.
// Concepto clave: **reset de formulario** y **limpiar busqueda**.
function clearSearch() {
  document.getElementById('search-query').value='';
  document.getElementById('search-strategy').value='';
  document.getElementById('search-tipo').value='';
  document.getElementById('search-k').value=5;
  document.getElementById('search-k-val').textContent=5;
  document.getElementById('search-results').innerHTML='';
}
