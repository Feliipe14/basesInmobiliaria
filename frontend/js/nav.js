/* ─── Navegación ─────────────────────────────────────────────────────────── */

// Navega entre las secciones de la aplicacion (una sola pagina o SPA).
// Oculta todas las secciones, muestra la solicitada y activa el boton del menu.
// Tambien carga datos on-demand segun la seccion (imagenes, evaluaciones).
// Concepto clave: **navegacion SPA** y **carga perezosa**.
function navigate(section, el) {
  document.querySelectorAll('.section').forEach(function (s) { s.classList.remove('active'); });
  document.querySelectorAll('.nav-item').forEach(function (n) { n.classList.remove('active'); });
  document.getElementById('sec-' + section).classList.add('active');
  if (el) el.classList.add('active');
  if (section === 'images' && !window._imagesLoaded) loadImages();
  if (section === 'evaluations') loadEvaluations();
}
