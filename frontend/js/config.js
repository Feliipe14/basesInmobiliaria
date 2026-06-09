/* ─── Configuración global ──────────────────────────────────────────────── */

// URL base del backend FastAPI. Todas las peticiones apuntan aqui.
// Concepto clave: **API REST** y **endpoint**.
const API = 'http://localhost:8000';

const QUERIES = [
  '¿Se permiten mascotas en el apartamento?',
  '¿Cuál es el valor del arriendo mensual?',
  '¿Qué incluye el contrato de arrendamiento?',
  '¿Cuántas habitaciones tiene la propiedad?',
  '¿Qué servicios públicos están incluidos?',
];

// Funcion hash para convertir cualquier texto en un numero entero.
// Se usa para asignar colores consistentes a cada propiedad.
// Concepto clave: **funcion hash** y **color determinista**.
function hashStr(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) - h) + s.charCodeAt(i);
    h |= 0;
  }
  return Math.abs(h);
}

// Selecciona una clase CSS de placeholder segun el ID de la propiedad.
// El hash asegura que la misma propiedad siempre obtenga el mismo color.
// Concepto clave: **clase CSS dinamica** y **placeholder visual**.
function imgPlaceholderClass(propertyId) {
  const idx = hashStr(propertyId || '') % 5;
  return 'img-ph-' + idx;
}
