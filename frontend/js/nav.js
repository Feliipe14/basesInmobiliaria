/* ─── Navegación ─────────────────────────────────────────────────────────── */

function navigate(section, el) {
  document.querySelectorAll('.section').forEach(function (s) { s.classList.remove('active'); });
  document.querySelectorAll('.nav-item').forEach(function (n) { n.classList.remove('active'); });
  document.getElementById('sec-' + section).classList.add('active');
  if (el) el.classList.add('active');
  if (section === 'images' && !window._imagesLoaded) loadImages();
  if (section === 'evaluations') loadEvaluations();
}
