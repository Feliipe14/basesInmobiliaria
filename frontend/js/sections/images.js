/* ─── Imágenes: Galería, Búsqueda imagen→imagen, texto→imagen ──────────── */

// ─── Helper: placeholder elegante (fallback cuando la URL falla) ─────────

// Construye un placeholder visual generico para cuando la URL de la imagen falla.
// Muestra el icono del edificio, el ID de la propiedad y una etiqueta.
// Concepto clave: **fallback visual** y **placeholder**.
function buildImgPlaceholder(propertyId, tipo, height) {
  height = height || 'h-40';
  var phClass = imgPlaceholderClass(propertyId);
  var tipoLabel = escHtml(tipo || 'Imagen');
  return '<div class="' + phClass + ' ' + height + ' flex flex-col items-center justify-center gap-1 p-3 text-center">' +
    buildingIcon(48) +
    '<span class="text-xs font-mono font-bold text-white/50">' + escHtml(propertyId || '—') + '</span>' +
    '<span class="badge badge-tipo" style="font-size:10px">' + tipoLabel + '</span>' +
  '</div>';
}

// ─── Helper: tarjeta de imagen con <img> real + fallback a placeholder ───

/**
 * Renderiza un contenedor con una <img> real apuntando a picsum.
 * Si la imagen falla al cargar (onerror) se muestra el placeholder CSS clásico.
 */
// Renderiza un contenedor con un elemento img real que apunta al servidor de imagenes.
// Si la imagen falla al cargar, automaticamente se reemplaza por el placeholder.
// Concepto clave: **carga de imagen** y **fallback automatico**.
function buildImgWithFallback(propertyId, url, tipo, height, extraAttrs) {
  height = height || 'h-40';
  var phClass = imgPlaceholderClass(propertyId);
  var tipoLabel = escHtml(tipo || 'Imagen');
  extraAttrs = extraAttrs || '';
  // ID único para el contenedor, así onerror puede referenciarlo
  var containerId = 'img-c-' + (Math.random().toString(36).slice(2, 10));

  return '<div id="' + containerId + '" class="relative ' + height + ' overflow-hidden rounded-lg" style="background:#1a1a2e">' +
    '<img src="' + escHtml(url) + '" alt="' + escHtml(propertyId) + '" class="w-full h-full object-cover" ' + extraAttrs +
      ' onerror="this.onerror=null;this.style.display=\'none\';var c=document.getElementById(\'' + containerId + '\');if(c)c.innerHTML=\'' +
        escHtml(buildImgPlaceholderInner(propertyId, tipo)) + '\';" ' +
      'onload="this.style.opacity=\'1\'" style="opacity:0;transition:opacity 0.3s" />' +
  '</div>';
}

/** Versión inline del placeholder (sin el wrapper <div>). */
// Version inline del placeholder, sin el div contenedor externo.
// Se usa dentro del onerror de la imagen para reemplazar el contenido.
// Concepto clave: **placeholder inline** y **fallback interno**.
function buildImgPlaceholderInner(propertyId, tipo) {
  var phClass = imgPlaceholderClass(propertyId);
  var tipoLabel = escHtml(tipo || 'Imagen');
  return '<div class="' + phClass + ' w-full h-full flex flex-col items-center justify-center gap-1 p-3 text-center">' +
    buildingIcon(48) +
    '<span class="text-xs font-mono font-bold text-white/50">' + escHtml(propertyId || '—') + '</span>' +
    '<span class="badge badge-tipo" style="font-size:10px">' + tipoLabel + '</span>' +
  '</div>';
}

// ─── Helper: buildImgCard con imagen real ────────────────────────────────

// Construye una tarjeta completa de imagen con foto real y boton de busqueda similar.
// Al hacer clic en el boton, dispara la busqueda de imagenes parecidas.
// Concepto clave: **tarjeta de imagen** y **accion de busqueda**.
function buildImgCard(img, onClickAttr) {
  onClickAttr = onClickAttr || '';
  var tipoLabel = escHtml(img.tipo || 'Imagen');
  return '<div class="img-card"' + onClickAttr + '>' +
    buildImgWithFallback(img.property_id, img.url, img.tipo, 'h-40') +
    '<div class="p-2">' +
      '<div class="flex items-center justify-between">' +
        '<span class="text-xs font-mono text-text-muted truncate">' + escHtml(img.property_id) + '</span>' +
        '<span class="badge badge-tipo text-xs">' + tipoLabel + '</span>' +
      '</div>' +
      '<button class="btn-primary w-full mt-2 text-xs py-1.5 justify-center">' +
        '<svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>' +
        ' Buscar similares' +
      '</button>' +
    '</div>' +
  '</div>';
}

// ─── Cargar galería ───────────────────────────────────────────────────────

// Carga la galeria de imagenes desde la API, mostrando skeletons mientras espera.
// Obtiene 20 imagenes aleatorias y las renderiza como tarjetas clickeables.
// Concepto clave: **carga de galeria** y **skeleton loader**.
async function loadImages() {
  var gallery = document.getElementById('img-gallery');
  gallery.innerHTML = createSkeletonLoader(8,'h-44');
  try {
    var r = await fetch(API + '/search/image/random?top_k=20');
    if (!r.ok) throw new Error('Error cargando imágenes');
    var d = await r.json();
    window._imagesLoaded = true;
    window._imageData = d.resultados || [];

    if (!window._imageData.length) {
      gallery.innerHTML = '<div class="col-span-4 text-text-muted text-sm p-4 text-center">No se encontraron imágenes en la base de datos.</div>';
      return;
    }

    gallery.innerHTML = window._imageData.map(function (img) {
      return buildImgCard(img, ' onclick="searchSimilar(\'' + escHtml(img.media_id) + '\',\'' + escHtml(img.url) + '\')"');
    }).join('');
  } catch(e) {
    gallery.innerHTML = '<div class="col-span-4">' + createSkeletonLoader(1,'h-20') + '<div class="text-xs text-red-400 mt-2">' + escHtml(e.message) + '</div></div>';
  }
}

// ─── Búsqueda imagen→imagen ──────────────────────────────────────────────

// Busca imagenes similares a una imagen dada, usando su media_id.
// Muestra la imagen fuente y los resultados ordenados por score de similitud.
// Concepto clave: **busqueda imagen a imagen** y **similitud visual**.
async function searchSimilar(mediaId, sourceUrl) {
  document.getElementById('img-gallery-panel').classList.add('hidden');
  document.getElementById('img-tab-panel-t2i').classList.remove('active');
  var panel = document.getElementById('img-similar-panel');
  panel.classList.remove('hidden');
  document.getElementById('similar-source-id').textContent = mediaId;

  document.getElementById('img-breadcrumb').innerHTML =
    '<span class="cursor-pointer hover:text-accent-blue" onclick="showGallery()">Galería</span>' +
    '<span class="text-text-muted">→</span>' +
    '<span class="text-text-main">Similares a <span class="font-mono text-accent-cyan text-xs">' + escHtml(mediaId) + '</span></span>';

  // Source image — con imagen real + fallback
  document.getElementById('img-source-card').innerHTML =
    '<div class="flex items-center gap-3 p-3 rounded-lg" style="background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.25)">' +
      '<div class="w-20 h-20 rounded-lg overflow-hidden flex-shrink-0" style="background:#1a1a2e">' +
        '<img src="' + escHtml(sourceUrl) + '" alt="' + escHtml(mediaId) + '" class="w-full h-full object-cover" ' +
          'onerror="this.onerror=null;var p=this.parentElement;p.innerHTML=\'' +
            escHtml(buildingIcon(28)) + '\';p.className=\'w-20 h-20 rounded-lg flex flex-col items-center justify-center gap-0.5 \' + imgPlaceholderClass(\'' + escHtml(mediaId) + '\');" ' +
          'onload="this.style.opacity=\'1\'" style="opacity:0;transition:opacity 0.3s" />' +
      '</div>' +
      '<div>' +
        '<div class="text-xs text-text-muted mb-1">Imagen fuente</div>' +
        '<div class="font-mono text-xs text-accent-cyan">' + escHtml(mediaId) + '</div>' +
      '</div>' +
    '</div>';

  var resultsEl = document.getElementById('img-similar-results');
  resultsEl.innerHTML = createSkeletonLoader(6,'h-40');

  try {
    var r = await fetch(API + '/search/image', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({media_id:mediaId, top_k:6}),
    });
    if (!r.ok) throw new Error('Error buscando similares');
    var d = await r.json();
    var imgs = d.resultados || [];
    if (!imgs.length) {
      resultsEl.innerHTML = '<div class="col-span-3 text-text-muted text-sm p-4">No se encontraron imágenes similares.</div>';
      return;
    }
    resultsEl.innerHTML = imgs.map(function (img) {
      return '<div class="img-card">' +
        '<div class="relative h-36">' +
          buildImgWithFallback(img.property_id, img.url, img.tipo, 'h-36') +
          '<span class="absolute top-2 right-2 score-badge ' + scoreClass(img.score) + '">' + img.score.toFixed(3) + '</span>' +
        '</div>' +
        '<div class="p-2 text-xs font-mono text-text-muted truncate">' + escHtml(img.property_id) + '</div>' +
      '</div>';
    }).join('');
  } catch(e) {
    resultsEl.innerHTML = '<div class="col-span-3 text-red-400 text-sm">' + escHtml(e.message) + '</div>';
  }
}

// Vuelve a mostrar la galeria principal ocultando el panel de resultados similares.
// Restaura el breadcrumb de navegacion a "Galeria".
// Concepto clave: **navegacion hacia atras** y **galeria principal**.
function showGallery() {
  document.getElementById('img-similar-panel').classList.add('hidden');
  document.getElementById('img-gallery-panel').classList.remove('hidden');
  document.getElementById('img-breadcrumb').innerHTML = '<span class="text-text-main">Galería</span>';
  // Switch tab back to gallery
  switchImgTab('gallery');
}

// ─── Tabs: Galería ↔ Búsqueda por descripción ─────────────────────────────

// Cambia entre las pestanas de la seccion de imagenes: galeria y busqueda por descripcion.
// Activa la pestana seleccionada y oculta la otra.
// Concepto clave: **pestanas** y **cambio de vista**.
function switchImgTab(tab) {
  document.querySelectorAll('.img-tab').forEach(function (t) { t.classList.remove('active'); });
  document.querySelectorAll('.img-tab-panel').forEach(function (p) { p.classList.remove('active'); });
  var tabEl = document.querySelector('.img-tab[data-tab="' + tab + '"]');
  if (tabEl) tabEl.classList.add('active');
  var panel = document.getElementById('img-tab-panel-' + tab);
  if (panel) panel.classList.add('active');
}

// ─── Búsqueda texto→imagen ────────────────────────────────────────────────

var T2I_EXAMPLES = [
  'Apartamento moderno',
  'Sala amplia',
  'Vista exterior fachada',
  'Habitación principal',
];

// Llena el campo de busqueda texto a imagen con un ejemplo predefinido.
// Resalta visualmente el boton de ejemplo seleccionado.
// Concepto clave: **ejemplos de busqueda** y **query predefinida**.
function fillT2iQuery(q, btn) {
  document.getElementById('t2i-query').value = q;
  document.querySelectorAll('#t2i-examples .btn-query').forEach(function (b) { b.classList.remove('selected'); });
  if (btn) btn.classList.add('selected');
}

// Ejecuta la busqueda de imagenes a partir de una descripcion textual.
// Envia la consulta a la API y muestra los resultados ordenados por relevancia.
// Concepto clave: **texto a imagen** y **busqueda multimodal**.
async function doTextToImage() {
  var query = document.getElementById('t2i-query').value.trim();
  if (!query) { showToast('Describe la propiedad que buscas','error'); return; }
  var resultsEl = document.getElementById('t2i-results');
  setLoading('btn-t2i', true);
  resultsEl.innerHTML = createSkeletonLoader(5,'h-44');

  try {
    var r = await fetch(API + '/search/text-to-image', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({query:query, top_k:5}),
    });
    if (!r.ok) throw new Error('Error en búsqueda texto→imagen');
    var d = await r.json();
    var imgs = d.resultados || [];

    if (!imgs.length) {
      resultsEl.innerHTML = '<div class="col-span-4 text-text-muted text-sm p-4 text-center">No se encontraron imágenes para esta descripción.</div>';
      return;
    }

    resultsEl.innerHTML = imgs.map(function (img) {
      return '<div class="img-card" onclick="searchSimilar(\'' + escHtml(img.media_id) + '\',\'' + escHtml(img.url) + '\')">' +
        '<div class="relative h-40">' +
          buildImgWithFallback(img.property_id, img.url, img.tipo, 'h-40') +
          '<span class="absolute top-2 right-2 score-badge ' + scoreClass(img.score) + '">' + img.score.toFixed(3) + '</span>' +
        '</div>' +
        '<div class="p-2">' +
          '<div class="flex items-center justify-between">' +
            '<span class="text-xs font-mono text-text-muted truncate">' + escHtml(img.property_id) + '</span>' +
            '<span class="badge badge-tipo text-xs">' + escHtml(img.tipo||'') + '</span>' +
          '</div>' +
          '<div class="text-[10px] text-text-muted mt-1 font-mono">Score: ' + img.score.toFixed(4) + '</div>' +
        '</div>' +
      '</div>';
    }).join('');
  } catch(e) {
    showError('t2i-results', e.message);
  } finally {
    setLoading('btn-t2i', false);
  }
}
