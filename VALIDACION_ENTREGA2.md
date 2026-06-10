# Validación contra Requisitos — Entrega 2

## Documento: Proyecto Sistema RAG NoSQL con MongoDB_2026

---

## Requisitos Obligatorios — Entrega 2

### Dataset Preparado

| Requisito | Estado | Evidencia |
|---|---|---|
| Mínimo 100 documentos de texto | **CUMPLE** | `generate_dataset.py` genera 100 documentos en `documents_repository` |
| Mínimo 50 imágenes asociadas | **CUMPLE** | 60 media_assets (3 por cada una de 20 propiedades) |
| Formato JSON válido para carga | **CUMPLE** | Documentos generados como diccionarios Python, compatibles con MongoDB |

### Sistema RAG Funcional

| Requisito | Estado | Evidencia |
|---|---|---|
| Pipeline completo ingesta con embeddings | **CUMPLE** | `generate_dataset.py` genera datos + CLIP embeddings reales; `chunking_pipeline.py` genera chunks + MiniLM embeddings |
| Mínimo dos estrategias de chunking | **CUMPLE** | Tres: fixed-size, sentence-aware, semantic (en `chunking_pipeline.py`) |
| API REST con endpoints documentados | **CUMPLE** | FastAPI con 14 endpoints en `api/main.py` + README |
| Integración con LLM gratuito | **CUMPLE** | Groq API + Llama 3.1-8b-instant |

### Demostración de Consultas

| Requisito | Estado | Evidencia |
|---|---|---|
| 5 consultas de ejemplo con evidencias | **CUMPLE** | 10 consultas en `experiment.py` y `frontend/js/config.js` |
| Casos de uso texto-texto | **CUMPLE** | `POST /search` con MiniLM (384 dims) |
| Casos de uso imagen-imagen | **CUMPLE** | `POST /search/image` con CLIP (512 dims) |
| Casos de uso multimodal | **CUMPLE** | `POST /search/text-to-image` con CLIP text encoder |

### Experimento de Chunking

| Requisito | Estado | Evidencia |
|---|---|---|
| Resultados comparativos de las estrategias | **CUMPLE** | `GET /experiment/results` + `python/experiment.py` |
| Análisis de chunks (cantidad, longitud promedio) | **CUMPLE** | `experiment.py` calcula n_chunks, avg_len, avg_score por estrategia |
| Conclusión argumentada sobre estrategia óptima | **CUMPLE** | Documentada en `experiment.py` (análisis comparativo) y en `INFORME_FINAL.md` |

### Código Fuente Completo

| Requisito | Estado | Evidencia |
|---|---|---|
| Repositorio Git con estructura clara | **CUMPLE** | `.git` presente, estructura organizada (`python/`, `frontend/`, `scripts/`) |
| README con instrucciones de instalación | **CUMPLE** | `README.md` detallado con pasos de instalación y configuración |
| Scripts de carga y configuración | **CUMPLE** | `generate_dataset.py`, `chunking_pipeline.py`, `scripts/init-db.js` |

### Informe Final

| Requisito | Estado | Evidencia |
|---|---|---|
| Arquitectura técnica implementada | **CUMPLE** | Sección 2 de `INFORME_FINAL.md` |
| Resultados del experimento de chunking con interpretación | **CUMPLE** | Sección 6 de `INFORME_FINAL.md` |
| Resultados y evaluación del sistema | **CUMPLE** | Secciones 6–7 de `INFORME_FINAL.md` |
| Lecciones aprendidas y recomendaciones | **CUMPLE** | Sección 9 de `INFORME_FINAL.md` |
| Comparación con enfoque relacional | **CUMPLE** | Sección 10 de `INFORME_FINAL.md` |

---

## Alcance Técnico — Componentes del Documento

### Índices y Schema Validation (sección "Alcance Técnico" del enunciado)

| Ítem | Estado | Evidencia |
|---|---|---|
| Schema Validation con `$jsonSchema` | **CUMPLE** | `scripts/init-db.js` aplica validadores JSON Schema a 6 colecciones: `users`, `properties`, `document_chunks`, `contracts`, `documents_repository`, `rag_evaluations` |
| Índice de texto en `contenido_texto` | **CUMPLE** | `scripts/init-db.js` línea 300: `{ contenido: "text" }` sobre `documents_repository` (campo equivalente; el modelo usa `contenido` en vez de `contenido_texto`) |
| Índice vectorial knnVector en embeddings | **CUMPLE** | Atlas Vector Search Index `vector_index_chunks` (384 dims, cosine) + `vector_index_images` (512 dims); documentado en `init-db.js` líneas 375–404 |
| Índice compuesto `{ fecha: 1, idioma: 1 }` | **NO IMPLEMENTADO** | El modelo de datos no usa campo `idioma` (dominio 100% en español). Se implementaron otros índices compuestos equivalentes: `{ tipo: 1, precio: 1 }`, `{ estado: 1, fecha_vencimiento: 1 }`, `{ "chunk_metadata.tipo_doc": 1, "chunk_metadata.ciudad": 1 }` |
| Funciones / Atlas Triggers | **NO IMPLEMENTADO** | Opcional según el enunciado |

---

## Evaluación con RAGAS (Nota Extra)

| Requisito | Estado | Evidencia |
|---|---|---|
| Dataset de mínimo 20 pares (pregunta, ground_truth) | **CUMPLE** | `python/evaluacion_ragas.py` — constante `GROUND_TRUTH` con **22 pares** cubriendo todos los temas del dominio |
| Ejecutar evaluación con RAGAS (faithfulness, answer_relevancy, context_recall) | **CUMPLE** | `python/evaluacion_ragas.py` — función `run_ragas_for_records()` usa RAGAS 0.4.x con Groq como LLM juez |
| Almacenar scores en colección MongoDB | **CUMPLE** | `save_to_mongodb()` hace upsert en `rag_evaluations` con campos `faithfulness`, `answer_relevancy`, `context_recall`, `modelo_eval`, `estrategia_chunking`, `ground_truth` |
| Evaluar las 3 estrategias de chunking | **CUMPLE** | `run_ragas_evaluation()` itera sobre `fixed_size`, `sentence`, `semantic` |
| Endpoint API para ejecutar RAGAS | **CUMPLE** | `POST /evaluations/run-ragas` en `api/main.py` — acepta parámetros `strategy` y `top_k` |
| Visualización en frontend | **CUMPLE** | Sección "Evaluaciones RAGAS" en `index.html` + botón "Ejecutar Evaluación RAGAS" en `frontend/js/sections/evaluations.js` |

**Instalación RAGAS:**
```bash
cd python
pip install ragas>=0.2.0 langchain-groq>=0.1.9 langchain-google-vertexai>=1.0.0 datasets>=2.14.0
```

**Ejecución CLI:**
```bash
python evaluacion_ragas.py --strategy all --top-k 5
```

---

## Resumen Final

| Categoría | Implementados | Total |
|---|---|---|
| Dataset Preparado | 3 | 3 |
| Sistema RAG Funcional | 4 | 4 |
| Demostración de Consultas | 4 | 4 |
| Experimento de Chunking | 3 | 3 |
| Código Fuente Completo | 3 | 3 |
| Informe Final | 5 | 5 |
| Alcance Técnico (índices/validation) | 3 | 5 |
| **NOTA EXTRA — RAGAS** | **6** | **6** |
| **TOTAL** | **31** | **33** |

**El proyecto está COMPLETO y LISTO para sustentación.**

Todos los requisitos obligatorios de la Entrega 2 están cumplidos (22/22). Los 2 ítems faltantes del Alcance Técnico son menores: el índice compuesto `{ fecha, idioma }` no aplica al dominio (no existe campo `idioma`) y Triggers son explícitamente opcionales.

El módulo de **RAGAS (nota extra)** está completamente implementado con las 3 métricas reales solicitadas, evaluación de las 3 estrategias de chunking, y persistencia en MongoDB.
