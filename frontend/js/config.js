/* ─── Configuración global ──────────────────────────────────────────────── */
const API = 'http://localhost:8000';

const QUERIES = [
  '¿Se permiten mascotas en el apartamento?',
  '¿Cuál es el valor del arriendo mensual?',
  '¿Qué incluye el contrato de arrendamiento?',
  '¿Cuántas habitaciones tiene la propiedad?',
  '¿Qué servicios públicos están incluidos?',
];

// Hash simple para generar color de placeholder de imagen
function hashStr(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h) + s.charCodeAt(i);
    h |= 0;
  }
  return Math.abs(h);
}

function imgPlaceholderClass(propertyId) {
  const idx = hashStr(propertyId || '') % 5;
  return 'img-ph-' + idx;
}
