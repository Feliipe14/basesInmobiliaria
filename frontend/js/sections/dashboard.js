/* ─── Dashboard ─────────────────────────────────────────────────────────── */

async function loadDashboard() {
  try {
    var r = await fetch(API + '/stats');
    if (!r.ok) throw new Error('Error al cargar stats');
    var d = await r.json();

    var statDefs = [
      {icon:'📄', label:'Documentos', val:d.documentos, sub:'en documents_repository', color:'accent-blue'},
      {icon:'🧩', label:'Chunks Totales', val:d.chunks_total, sub:'vectorizados en MongoDB', color:'accent-cyan'},
      {icon:'🏘️', label:'Propiedades', val:d.propiedades, sub:'en colección properties', color:'accent-gold'},
      {icon:'🖼️', label:'Imágenes', val:d.media_assets, sub:'con embeddings CLIP 512d', color:'accent-green'},
    ];

    document.getElementById('stat-cards').innerHTML = statDefs.map(function (s) {
      return '<div class="card-stat relative overflow-hidden">' +
        '<div class="absolute right-3 top-3 text-3xl opacity-20">' + s.icon + '</div>' +
        '<div class="text-xs text-text-muted uppercase tracking-wider mb-1">' + s.label + '</div>' +
        '<div class="text-3xl font-extrabold text-' + s.color + ' count-anim font-mono">' + s.val + '</div>' +
        '<div class="text-xs text-text-muted mt-1">' + s.sub + '</div>' +
      '</div>';
    }).join('');

    var total = d.chunks_total || 1;
    var strats = [
      {key:'fixed_size', label:'fixed_size', badge:'badge-fs', desc:'Predecible y rápido. Ideal para contratos largos.'},
      {key:'sentence', label:'sentence', badge:'badge-sn', desc:'Respeta oraciones. Ideal para chats y FAQs.'},
      {key:'semantic', label:'semantic', badge:'badge-sm', desc:'Mayor cohesión temática. Mejor score en consultas.'},
    ];
    document.getElementById('chunk-strategy-cards').innerHTML = strats.map(function (s) {
      var count = d.chunks_por_estrategia[s.key] || 0;
      var pct = Math.round(count/total*100);
      return '<div class="card p-4">' +
        '<div class="flex items-center justify-between mb-2">' +
          '<span class="badge ' + s.badge + '">' + s.label + '</span>' +
          '<span class="text-xl font-bold font-mono text-text-main">' + count + '</span>' +
        '</div>' +
        '<div class="score-bar-wrap my-2"><div class="score-bar-fill" style="width:' + pct + '%;background:var(--accent-blue)"></div></div>' +
        '<div class="text-xs text-text-muted">' + pct + '% del total — ' + s.desc + '</div>' +
      '</div>';
    }).join('');

    document.getElementById('dash-eval-count').textContent = d.evaluaciones;
    document.getElementById('dash-log-count').textContent = d.consultas_log;
  } catch(e) {
    document.getElementById('stat-cards').innerHTML = '<div class="col-span-4 text-text-muted text-sm p-4">No se pudieron cargar las estadísticas. Verifica que la API esté activa.</div>';
  }

  var container = document.getElementById('example-queries-dash');
  container.innerHTML = QUERIES.map(function (q, i) {
    return '<div class="card p-4 cursor-pointer hover:border-accent-blue transition-colors" onclick="goToRag(\'' + q.replace(/'/g,"\\'") + '\')">' +
      '<div class="text-xs text-text-muted font-mono mb-1">#' + (i+1) + '</div>' +
      '<div class="text-sm text-text-main mb-2">' + escHtml(q) + '</div>' +
      '<div class="text-xs text-accent-blue flex items-center gap-1">→ Probar en RAG</div>' +
    '</div>';
  }).join('');
}

function goToRag(query) {
  document.getElementById('rag-query').value = query;
  var navItem = document.querySelector('[data-section="rag"]');
  navigate('rag', navItem);
  highlightRagBtn(query);
}
