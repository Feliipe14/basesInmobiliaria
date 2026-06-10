# Informe Final — Sistema RAG Inmobiliario con MongoDB NoSQL

## Bases de Datos No Relacionales — Proyecto Final

---

## 1. Resumen Ejecutivo

Este proyecto implementa un sistema **RAG** (Retrieval-Augmented Generation) para el dominio inmobiliario de Manizales, Colombia, utilizando **MongoDB Atlas** como base de datos NoSQL principal. El sistema integra búsqueda semántica multimodal (texto e imágenes) con un LLM gratuito (Groq + Llama 3.1) para responder preguntas complejas sobre propiedades, contratos y documentos legales.

El sistema almacena y procesa **100 documentos de texto** y **60 imágenes asociadas a 20 propiedades**, utilizando tres estrategias de chunking (fixed-size, sentence-aware, semántico) para determinar el impacto de la fragmentación en la calidad de las respuestas RAG.

Como componente de **nota extra**, se implementó un módulo completo de evaluación automática con el framework **RAGAS 0.4.x**, que mide las tres métricas estándar de calidad RAG: Faithfulness, Answer Relevancy y Context Recall, usando Groq como LLM juez.

---

## 2. Arquitectura Técnica Implementada

### 2.1 Diagrama de Arquitectura

```
[Frontend HTML/JS]  ──►  [API FastAPI (Python)]  ──►  [MongoDB Atlas]
                                    │
                                    ├──► [Groq API (Llama 3.1)]  ← RAG + RAGAS juez
                                    │
                                    └──► [RAGAS 0.4.x + MiniLM]  ← evaluación automática
```

### 2.2 Componentes del Sistema

| Componente         | Tecnología                                        | Propósito                                            |
| ------------------ | ------------------------------------------------- | ---------------------------------------------------- |
| Base de Datos      | MongoDB Atlas M0 (512 MB)                         | Almacenamiento NoSQL + Vector Search                 |
| API                | Python FastAPI                                    | 14 endpoints REST para búsqueda, RAG y evaluación    |
| Frontend           | HTML + CSS + JavaScript vanilla                   | Interfaz SPA con sección de evaluaciones RAGAS       |
| Embeddings Texto   | sentence-transformers/all-MiniLM-L6-v2 (384 dims) | Búsqueda semántica texto-texto                       |
| Embeddings Imagen  | openai/clip-vit-base-patch32 (512 dims)           | Búsqueda multimodal texto-imagen e imagen-imagen     |
| LLM                | Groq API + Llama 3.1-8b-instant                   | Generación de respuestas + LLM juez en RAGAS         |
| Chunking           | langchain + lógica personalizada                  | 3 estrategias: fixed-size, sentence-aware, semántico |
| Evaluación         | RAGAS 0.4.x + HuggingFaceEmbeddings               | Métricas reales: faithfulness, answer_relevancy, context_recall |

### 2.3 Estrategia de Modelado NoSQL

Siguiendo las recomendaciones del documento del proyecto, se aplicaron tres estrategias de diseño:

**Embedded (datos incrustados):**
- Ratings y scores calculados se almacenan directamente en el documento de propiedad
- Historial de consultas del usuario como subdocumentos
- Metadatos pequeños como ubicación y características van dentro de la propiedad

**Referenced (referencias entre colecciones):**
- Las imágenes (`media_assets`) referencian a propiedades mediante `property_id`
- Los usuarios referencian agencias mediante `agency_id`
- Los chunks referencian documentos fuente mediante `doc_id`
- Los contratos referencian propiedades y usuarios involucrados

**Híbrido (mixto):**
- El documento principal de propiedad tiene `media_ids` como arreglo de referencias
- Pero los embeddings de metadatos se almacenan junto al chunk
- Las evaluaciones RAGAS coexisten con las evaluaciones proxy en la misma colección `rag_evaluations`, diferenciadas por el campo `modelo_eval`

---

## 3. Colecciones MongoDB (14 colecciones)

| #   | Colección              | Propósito                                                   | Documentos           |
| --- | ---------------------- | ----------------------------------------------------------- | -------------------- |
| 1   | `users`                | Usuarios del sistema (propietarios, agentes, arrendatarios) | 13                   |
| 2   | `agencies`             | Agencias inmobiliarias                                      | 3                    |
| 3   | `properties`           | Propiedades con datos estructurados y coordenadas GeoJSON   | 20                   |
| 4   | `media_assets`         | URLs de imágenes reales de Unsplash por propiedad           | 60                   |
| 5   | `listings`             | Publicaciones de venta o arriendo                           | 20                   |
| 6   | `contracts`            | Contratos con cláusulas y fechas                            | 15                   |
| 7   | `reviews`              | Reseñas de propiedades por arrendatarios                    | 20                   |
| 8   | `maintenance_requests` | Solicitudes de mantenimiento                                | 10                   |
| 9   | `documents_repository` | Documentos fuente del dominio inmobiliario                  | 100                  |
| 10  | `document_chunks`      | Chunks de texto vectorizados con MiniLM                     | ~900 (3 estrategias) |
| 11  | `image_embeddings`     | Embeddings de imagen generados con CLIP                     | 60                   |
| 12  | `rag_queries_logs`     | Registro de consultas realizadas al sistema                 | Variable             |
| 13  | `rag_evaluations`      | Evaluaciones proxy + evaluaciones RAGAS reales              | Variable             |
| 14  | `chat_sessions`        | Sesiones de chat                                            | 15                   |

### 3.1 Ejemplo de Documento: `properties`

```json
{
  "_id": "prop_001",
  "owner_id": "u_001",
  "titulo": "Moderno apartamento en El Cable",
  "ubicacion": {
    "ciudad": "Manizales",
    "geo": { "type": "Point", "coordinates": [-75.517, 5.068] }
  },
  "caracteristicas": { "area": 75, "habitaciones": 2, "banos": 2 },
  "media_ids": ["med_prop_001_01", "med_prop_001_02", "med_prop_001_03"]
}
```

### 3.2 Ejemplo de Documento: `document_chunks`

```json
{
  "_id": "chunk_sem_doc_001_0002",
  "doc_id": "doc_001",
  "texto": "El contrato de arrendamiento establece...",
  "estrategia_chunking": "semantic",
  "chunk_index": 2,
  "embedding": [0.023, -0.015, "...384 dims"],
  "modelo_embedding": "all-MiniLM-L6-v2",
  "chunk_metadata": { "tipo_doc": "contrato", "ciudad": "Manizales" }
}
```

### 3.3 Ejemplo de Documento: `rag_evaluations` (con RAGAS real)

```json
{
  "_id": "ragas_sem_a1b2c3d4e5f6",
  "question": "¿Se permiten mascotas en el apartamento?",
  "faithfulness": 0.91,
  "answer_relevancy": 0.87,
  "context_recall": 0.78,
  "modelo_eval": "ragas-0.4.3",
  "modelo_llm": "llama-3.1-8b-instant",
  "estrategia_chunking": "semantic",
  "respuesta_generada": "Según el reglamento...",
  "ground_truth": "La política de mascotas varía según cada propiedad...",
  "fecha": "2026-06-10T16:30:00Z"
}
```

### 3.4 Schema Validation

Se implementaron validadores `$jsonSchema` en MongoDB para **6 colecciones** mediante `scripts/init-db.js`:

| Colección              | Campos obligatorios validados                                             |
| ---------------------- | ------------------------------------------------------------------------- |
| `users`                | `email` (formato regex), `roles` (enum: propietario/arrendatario/agente)  |
| `properties`           | `owner_id`, `ubicacion.geo` (GeoJSON Point válido)                        |
| `document_chunks`      | `doc_id`, `chunk_index`, `estrategia_chunking` (enum), `texto`, `embedding` |
| `contracts`            | `listing_id`, `arrendador_id`, `arrendatario_id`, `estado` (enum)        |
| `documents_repository` | `tipo`, `contenido`, `origen_id`                                          |
| `rag_evaluations`      | `rag_query_id`; campos RAGAS tipados como `double`                        |

---

## 4. Índices Implementados

### 4.1 Índices Regulares (`scripts/init-db.js`)

| Colección              | Índice                                             | Tipo        | Propósito                            |
| ---------------------- | -------------------------------------------------- | ----------- | ------------------------------------ |
| `users`                | `{ email: 1 }`                                     | Único       | Login y lookup por email             |
| `properties`           | `{ "ubicacion.geo": "2dsphere" }`                  | Geoespacial | Búsquedas por proximidad             |
| `documents_repository` | `{ contenido: "text" }`                            | Texto completo | Búsqueda full-text en documentos  |
| `documents_repository` | `{ origen_id: 1, tipo: 1 }`                        | Compuesto   | Filtros híbridos por origen y tipo   |
| `document_chunks`      | `{ "chunk_metadata.tipo_doc": 1, "chunk_metadata.ciudad": 1 }` | Compuesto | Filtros en búsqueda vectorial |
| `listings`             | `{ tipo: 1, precio: 1 }`                           | Compuesto   | Búsquedas por tipo y rango de precio |
| `contracts`            | `{ estado: 1, fecha_vencimiento: 1 }`              | Compuesto   | Contratos activos por vencimiento    |
| `rag_queries_logs`     | `{ timestamp: -1 }`                                | Simple      | Historial de consultas               |
| `image_embeddings`     | `{ media_id: 1 }`                                  | Simple      | Join con media_assets                |
| `reviews`              | `{ target_property_id: 1 }`                        | Simple      | Reseñas por propiedad                |

### 4.2 Índices Vectoriales (Atlas Vector Search)

| Nombre índice         | Colección          | Campo       | Dimensiones  | Similitud | Modelo          |
| --------------------- | ------------------ | ----------- | ------------ | --------- | --------------- |
| `vector_index_chunks` | `document_chunks`  | `embedding` | 384 (MiniLM) | cosine    | all-MiniLM-L6-v2 |
| `vector_index_images` | `image_embeddings` | `embedding` | 512 (CLIP)   | cosine    | clip-vit-base-patch32 |

Ambos índices se crearon desde la interfaz de Atlas UI → Search → Create Search Index → JSON Editor (no son creables con `createIndex` estándar en M0).

---

## 5. Estrategias de Chunking

### 5.1 Fixed-Size

Divide el texto en fragmentos de tamaño fijo (1024 caracteres, ~256 tokens) con superposición de 128 caracteres (~32 tokens). Implementado con `RecursiveCharacterTextSplitter` de LangChain.

**Cuándo usar:** Textos homogéneos, documentos sin estructura semántica clara, ingesta rápida.

### 5.2 Sentence-Aware

Respeta los límites de oraciones usando regex para español. Agrupa hasta 5 oraciones por chunk con superposición de 1 oración.

**Cuándo usar:** Textos narrativos, descripciones de propiedades, chats.

### 5.3 Semántico

Agrupa oraciones por similitud semántica usando embeddings de MiniLM. Umbral de coseno: 0.80. Cuando la similitud entre oraciones adyacentes cae por debajo del umbral, comienza un nuevo chunk (con overlap de 1 oración).

**Cuándo usar:** Documentos técnicos, contratos legales, textos con cambios de tema bien delimitados.

---

## 6. Resultados del Experimento de Chunking

### 6.1 Metodología

Se ejecutaron **10 consultas de prueba** sobre las 3 estrategias de chunking. Para cada consulta se midió: cantidad de chunks recuperados, longitud promedio, score de similitud coseno y tiempo de respuesta.

| #   | Consulta                                          | Categoría               |
| --- | ------------------------------------------------- | ----------------------- |
| 1   | "¿Se permiten mascotas en el apartamento?"        | Reglas y políticas      |
| 2   | "¿Cuál es el valor del arriendo mensual?"         | Costos y precios        |
| 3   | "¿Cuántas habitaciones tiene la propiedad?"       | Características físicas |
| 4   | "¿Qué incluye el contrato de arrendamiento?"      | Documentos legales      |
| 5   | "¿Cuál es la ubicación exacta del inmueble?"      | Ubicación               |
| 6   | "¿Qué servicios públicos están incluidos?"        | Servicios               |
| 7   | "¿Hay restricciones para subarrendar?"            | Reglamentos             |
| 8   | "¿Qué condiciones tiene el pago del canon?"       | Condiciones contractuales |
| 9   | "¿Cómo es la cocina del apartamento?"             | Amenidades              |
| 10  | "¿Qué opinan otros usuarios sobre la propiedad?"  | Opiniones               |

### 6.2 Resultados Cuantitativos (Score de similitud coseno)

| Consulta                        | Fixed-Size | Sentence   | Semantic       | Ganadora |
| ------------------------------- | ---------- | ---------- | -------------- | -------- |
| ¿Se permiten mascotas?          | 0.8467     | 0.8522     | **0.8872**     | Semantic |
| ¿Valor del arriendo mensual?    | 0.7627     | 0.7580     | **0.7985**     | Semantic |
| ¿Cuántas habitaciones tiene?    | 0.7601     | 0.7759     | **0.8141**     | Semantic |
| ¿Qué incluye el contrato?       | 0.8350     | 0.8380     | **0.8592**     | Semantic |
| ¿Ubicación exacta del inmueble? | 0.7742     | 0.7766     | **0.8159**     | Semantic |
| ¿Servicios públicos incluidos?  | 0.8153     | 0.8265     | **0.8724**     | Semantic |
| ¿Restricciones para subarrendar?| 0.7725     | 0.7725     | **0.7966**     | Semantic |
| ¿Condiciones del pago del canon?| 0.7944     | 0.8169     | **0.8497**     | Semantic |
| ¿Cómo es la cocina?             | 0.7954     | 0.7398     | **0.8100**     | Semantic |
| ¿Opiniones de otros usuarios?   | 0.7476     | 0.7649     | **0.7816**     | Semantic |

**Resumen global por estrategia:**

| Métrica                   | Fixed-Size | Sentence | Semantic       |
| ------------------------- | ---------- | -------- | -------------- |
| Total chunks en BD        | 412        | 561      | 2143           |
| Longitud promedio (chars) | 777.8      | 481.5    | 237.2          |
| Score promedio global     | 0.7904     | 0.7921   | **0.8285**     |
| Consultas ganadas         | 0 / 10     | 0 / 10   | **10 / 10**    |

### 6.3 Interpretación

La estrategia **semántica** ganó las 10 consultas con score promedio **0.8285**, superando a sentence (0.7921) y fixed-size (0.7904). Esto se debe a que el chunking semántico agrupa oraciones por tema, produciendo chunks temáticamente coherentes que `$vectorSearch` empareja mejor con la intención de la consulta.

La estrategia semántica produce chunks más cortos (237 caracteres promedio vs. 778 de fixed-size) porque los documentos inmobiliarios cambian frecuentemente de tema (cláusulas de contrato, descripción, precio, ubicación). Esto genera más chunks pero de mayor precisión temática.

### 6.4 Conclusión

Para el dominio inmobiliario, la estrategia **semántica** ofrece la mejor precisión de búsqueda vectorial. La estrategia **sentence** es la más equilibrada en términos de cobertura vs. calidad. Se recomienda un enfoque híbrido: `semantic` para contratos y reglamentos, `sentence` para descripciones de propiedades y chats.

---

## 7. Evaluación con RAGAS (Nota Extra)

### 7.1 Qué es RAGAS

RAGAS es un framework de evaluación automática para sistemas RAG que mide la calidad objetiva usando un LLM como juez. A diferencia de las métricas proxy (similitud coseno), RAGAS evalúa si las respuestas son **fieles al contexto** y **relevantes para la pregunta**.

### 7.2 Configuración Técnica

| Componente       | Implementación                                                                  |
| ---------------- | ------------------------------------------------------------------------------- |
| LLM juez         | Groq API + `llama-3.1-8b-instant` vía endpoint OpenAI-compatible               |
| Embeddings       | RAGAS `HuggingFaceEmbeddings` con `all-MiniLM-L6-v2` (local, sin costo)       |
| API RAGAS        | 0.4.x — `llm_factory()` + `InstructorLLM` + `EvaluationDataset.from_list()`   |
| Dataset GT       | 22 pares pregunta/respuesta_ideal cubriendo todos los temas del dominio         |
| Estrategias eval | `fixed_size`, `sentence`, `semantic`                                            |

**Archivo principal:** `python/evaluacion_ragas.py`

### 7.3 Métricas Evaluadas

| Métrica             | Descripción                                                                  | Rango |
| ------------------- | ---------------------------------------------------------------------------- | ----- |
| **Faithfulness**    | ¿La respuesta generada está fundamentada en el contexto recuperado?          | 0–1   |
| **Answer Relevancy**| ¿La respuesta es pertinente para la pregunta original?                       | 0–1   |
| **Context Recall**  | ¿El contexto recuperado cubre lo que la respuesta ideal (ground truth) dice? | 0–1   |

### 7.4 Dataset de Ground Truth (22 pares)

Se construyó manualmente un dataset de 22 pares pregunta-respuesta ideal cubriendo todos los temas del dominio inmobiliario:

| Tema                        | Nro. preguntas | Ejemplo                                              |
| --------------------------- | -------------- | ---------------------------------------------------- |
| Políticas de mascotas       | 2              | ¿Se permiten mascotas en el apartamento?             |
| Arriendo y formas de pago   | 3              | ¿Cuáles son las formas de pago del arriendo?         |
| Número de habitaciones      | 2              | ¿Cuántos baños tiene el apartamento?                 |
| Cláusulas contractuales     | 2              | ¿Cuánto tiempo dura el contrato de arrendamiento?    |
| Ubicación de propiedades    | 2              | ¿En qué barrios de Manizales están disponibles?      |
| Servicios públicos          | 2              | ¿Quién paga los servicios públicos?                  |
| Restricciones de subarriendo| 2              | ¿Se puede subarrendar parte del inmueble?            |
| Condiciones del canon       | 1              | ¿Qué condiciones tiene el pago del canon?            |
| Cocinas y amenidades        | 2              | ¿El apartamento tiene parqueadero y cuarto útil?     |
| Opiniones de usuarios       | 1              | ¿Qué opinan otros usuarios sobre la propiedad?       |
| Reglamento de copropiedad   | 1              | ¿Cuáles son las normas del reglamento de copropiedad?|
| Proceso de arrendamiento    | 2              | ¿Qué documentos se necesitan para arrendar?          |

### 7.5 Pipeline de Evaluación

Para cada pregunta del ground truth y cada estrategia de chunking:

```
pregunta  ──►  vector_search() top-5  ──►  contexto (chunks)
                                                    │
                                                    ▼
                                         call_llm_for_eval()  ──►  respuesta LLM
                                                    │
                                                    ▼
                                 EvaluationDataset.from_list()
                                 [user_input, response, retrieved_contexts, reference]
                                                    │
                                                    ▼
                                  RAGAS evaluate(metrics=[Faithfulness,
                                                 AnswerRelevancy, ContextRecall])
                                                    │
                                                    ▼
                                  upsert en rag_evaluations (MongoDB)
```

### 7.6 Ejecución

```bash
# Evaluación de una sola estrategia (recomendado para prueba inicial, ~3-5 min)
python evaluacion_ragas.py --strategy semantic --top-k 5

# Evaluación completa de las 3 estrategias (~10-15 min)
python evaluacion_ragas.py --strategy all --top-k 5

# Desde la API (FastAPI en ejecución)
# POST http://localhost:8000/evaluations/run-ragas?strategy=semantic&top_k=5
```

Los resultados se visualizan en el frontend → sección **"Evaluaciones RAGAS"** con barras de color (verde ≥ 75%, amarillo 50-75%, rojo < 50%) y se almacenan en `rag_evaluations` para comparación entre estrategias.

---

## 8. Resultados y Evaluación del Sistema

### 8.1 Evaluación de Búsqueda Semántica (texto-texto)

| Consulta                         | Estrategia óptima | Score promedio | Observación                                    |
| -------------------------------- | ----------------- | -------------- | ---------------------------------------------- |
| "¿Se permiten mascotas?"         | semantic          | 0.8872         | Encontró chunks del FAQ y reglamentos          |
| "¿Valor del arriendo?"           | semantic          | 0.7985         | Chunks de contratos con cláusulas de canon     |
| "¿Cuántas habitaciones?"         | semantic          | 0.8141         | Descripciones de propiedades con datos exactos |
| "¿Qué incluye el contrato?"      | semantic          | 0.8592         | Agrupó múltiples cláusulas del mismo tema      |
| "¿Servicios públicos incluidos?" | semantic          | 0.8724         | Chunks de FAQ sobre servicios                  |

**Conclusión:** El sistema recupera consistentemente los chunks relevantes. La estrategia semántica domina en precisión vectorial para todos los tipos de consultas del dominio.

### 8.2 Evaluación de Búsqueda Multimodal

**Imagen a imagen:** El sistema retornó imágenes de fachadas similares con scores altos, demostrando que los embeddings CLIP capturan correctamente las características visuales.

**Texto a imagen:** "fachada moderna" → predominantemente `imagen_fachada`; "sala amplia" → `imagen_sala`. Confirma que CLIP alinea correctamente los espacios vectoriales de texto e imagen.

**Imagen a texto vía RAG:** Al seleccionar una imagen, el sistema identifica la propiedad asociada y permite consultas RAG sobre sus documentos, cerrando el ciclo multimodal completo.

### 8.3 Evaluación del Pipeline RAG (Cualitativa)

- **Relevancia del contexto:** Los 5 chunks recuperados siempre incluyen información pertinente
- **Calidad de la respuesta:** El LLM genera respuestas coherentes basadas exclusivamente en el contexto
- **Tiempo de respuesta:** ~5 segundos promedio (búsqueda + generación con Groq)
- **Trazabilidad:** Cada consulta queda registrada en `rag_queries_logs` con embedding, chunks usados y respuesta generada

### 8.4 Evaluación Automática con RAGAS (Cuantitativa)

Las métricas RAGAS para las 3 estrategias se obtienen ejecutando `python evaluacion_ragas.py`. Los resultados por muestra y los promedios por estrategia se almacenan en la colección `rag_evaluations` y son visibles en el frontend.

**Interpretación de las métricas:**
- Un **Faithfulness alto** (>0.8) indica que el LLM responde solo con lo que hay en el contexto, sin alucinar
- Un **Answer Relevancy alto** (>0.8) indica que la respuesta ataca directamente la pregunta planteada
- Un **Context Recall alto** (>0.7) indica que el vector search recupera los chunks que contienen la respuesta correcta

RAGAS permite una comparación objetiva entre estrategias más allá de la similitud coseno, capturando si el LLM realmente usa el contexto de forma fiel y relevante.

---

## 9. API REST — 14 Endpoints Documentados

| Método | Ruta                          | Propósito                                     |
| ------ | ----------------------------- | --------------------------------------------- |
| GET    | `/`                           | Health check                                  |
| GET    | `/stats`                      | Estadísticas del sistema (conteos por colección) |
| POST   | `/search`                     | Búsqueda vectorial texto-texto                |
| POST   | `/rag`                        | Pipeline RAG completo (embed → retrieve → LLM → log) |
| GET    | `/chunks/compare`             | Comparar las 3 estrategias para una consulta  |
| GET    | `/experiment/results`         | Ejecutar experimento 10 consultas × 3 estrategias |
| GET    | `/evaluations`                | Evaluaciones guardadas (proxy + RAGAS reales) |
| POST   | `/evaluations/run-ragas`      | Ejecutar evaluación RAGAS completa desde API  |
| GET    | `/images`                     | Listado del catálogo de imágenes              |
| POST   | `/search/image`               | Búsqueda imagen-imagen por `media_id`         |
| GET    | `/search/image/random`        | Galería aleatoria de imágenes                 |
| POST   | `/search/images`              | Alternativa de búsqueda imagen-imagen         |
| POST   | `/search/text-to-image`       | Búsqueda texto → imagen con CLIP              |

Documentación interactiva disponible en `http://localhost:8000/docs` (Swagger UI).

---

## 10. Pipeline Multimodal

### 10.1 Texto a Texto (RAG)

```
consulta del usuario
       │
       ▼
all-MiniLM-L6-v2 (embedding 384d)
       │
       ▼
$vectorSearch en document_chunks (vector_index_chunks)
       │
       ▼
top-k chunks recuperados + construcción de contexto
       │
       ▼
Groq + Llama 3.1 → respuesta basada en el contexto
       │
       ▼
log en rag_queries_logs + respuesta al usuario
```

### 10.2 Texto a Imagen (CLIP)

```
descripción textual ("fachada moderna")
       │
       ▼
CLIP text encoder (embedding 512d)
       │
       ▼
$vectorSearch en image_embeddings (vector_index_images)
       │
       ▼
imágenes visualmente similares con scores
```

### 10.3 Evaluación Automática (RAGAS)

```
pregunta del GT
       │
       ├──► vector_search()  ──►  contexts (chunks)
       │                                │
       │                                ▼
       └──────────────────►  call_llm_for_eval()  ──►  answer
                                        │
                                        ▼
                         EvaluationDataset (RAGAS 0.4.x)
                              [user_input, response,
                               retrieved_contexts, reference]
                                        │
                                        ▼
                           evaluate(Faithfulness,
                                    AnswerRelevancy,
                                    ContextRecall)
                                   LLM juez: Groq
                                        │
                                        ▼
                           upsert en rag_evaluations
```

---

## 11. Lecciones Aprendidas y Recomendaciones

### 11.1 Lecciones Aprendidas

1. **El chunking afecta directamente la calidad RAG**: La estrategia semántica superó a las demás en todas las consultas. La fragmentación correcta es la decisión más impactante en un sistema RAG.

2. **Las versiones de las librerías importan**: RAGAS 0.4.x rompió compatibilidad con `LangchainLLMWrapper` — ahora requiere su propio `llm_factory()` con `InstructorLLM`. Es esencial fijar versiones en `requirements.txt`.

3. **Groq es totalmente compatible con la API de OpenAI**: Al usar `openai.OpenAI(base_url="https://api.groq.com/openai/v1")`, cualquier librería que soporte OpenAI puede usar Groq sin cambiar el código de negocio.

4. **MongoDB Atlas Vector Search es intuitivo**: La integración de `$vectorSearch` con el Aggregation Framework permite búsquedas híbridas (vectorial + filtros tradicionales) en un solo pipeline.

5. **CLIP requiere hardware para producción**: Generar embeddings de imagen con CLIP en CPU toma ~40 segundos para 60 imágenes. En producción se recomienda GPU o un servicio de embeddings.

6. **Evaluación proxy vs. RAGAS**: Las métricas de similitud coseno miden qué tan similar es el embedding de la consulta a los chunks, pero no si el LLM usó ese contexto correctamente. RAGAS mide la calidad real de extremo a extremo.

### 11.2 Recomendaciones

1. **Búsqueda híbrida**: Combinar `$vectorSearch` con `$search` (texto completo) para mejorar la recuperación en consultas con términos exactos (nombres, precios, fechas).

2. **Cache de embeddings**: Almacenar en memoria los embeddings más consultados para reducir latencia en producción.

3. **Pipeline de actualización automática**: Implementar Atlas Triggers para re-vectorizar automáticamente cuando se agreguen nuevos documentos al repositorio.

4. **Ampliar el dataset RAGAS**: El dataset actual de 22 preguntas cubre los temas principales. Para evaluación en producción se recomienda 100+ pares con anotación de expertos del dominio inmobiliario.

5. **Estrategia híbrida de chunking**: Aplicar `semantic` para contratos y reglamentos (donde cada cláusula es un tema independiente) y `sentence` para descripciones narrativas de propiedades.

---

## 12. Comparación con Enfoque Relacional

| Aspecto                | SQL (Relacional)                                  | MongoDB (NoSQL)                                             |
| ---------------------- | ------------------------------------------------- | ----------------------------------------------------------- |
| **Modelado**           | Esquema rígido con tablas normalizadas            | Esquema flexible, documentos embebidos o referenciados      |
| **Embeddings**         | Tabla separada con JOINs costosos                 | Misma colección o colección dedicada con `$lookup`          |
| **Vector Search**      | No nativo, requiere extensión (pgvector)          | Nativo con Atlas Vector Search y `$vectorSearch`            |
| **Geoespacial**        | PostGIS (extensión separada)                      | Nativo con GeoJSON e índices 2dsphere                       |
| **Escalabilidad**      | Vertical principalmente                           | Horizontal nativa (sharding)                                |
| **Consultas híbridas** | Múltiples queries o funciones complejas           | Un solo pipeline con `$vectorSearch` + filtros              |
| **Schema Validation**  | Obligatorio (DDL, tipado estricto)                | Opcional, con `$jsonSchema` a nivel de documento            |
| **Evaluación RAG**     | Requiere almacenamiento separado para evaluaciones| `rag_evaluations` coexiste con los documentos del dominio   |
| **Flexibilidad**       | Cambios requieren migraciones (`ALTER TABLE`)     | Cambios sin downtime, documentos con campos distintos       |

**Conclusión:** MongoDB ofrece ventajas significativas para sistemas RAG al integrar de forma nativa el almacenamiento de documentos, búsqueda vectorial y consultas híbridas en una sola plataforma, sin necesidad de servicios externos ni migraciones de esquema.

---

## 13. Instrucciones de Instalación y Ejecución

```bash
# 1. Clonar repositorio y configurar entorno
git clone <repo-url>
cd basesInmobiliaria
cp .env.example .env
# Editar .env con MONGODB_URI y GROQ_API_KEY

# 2. Instalar dependencias Python
cd python
pip install -r requirements.txt

# 3. Generar dataset completo (datos + embeddings CLIP)
python generate_dataset.py

# 4. Ejecutar pipeline de chunking y embeddings de texto
python chunking_pipeline.py --strategy all

# 5. Iniciar API REST
python -m uvicorn api.main:app --reload --port 8000

# 6. En otra terminal: frontend estático
cd ..
python -m http.server 3000
# Abrir http://localhost:3000

# 7. (Opcional) Ejecutar evaluación RAGAS — nota extra
cd python
python evaluacion_ragas.py --strategy all --top-k 5
# O desde Swagger UI: POST http://localhost:8000/evaluations/run-ragas
```

---

## 14. Créditos

**Proyecto:** Sistema RAG NoSQL con MongoDB — Inmobiliaria Manizales

**Curso:** Bases de Datos No Relacionales

**Integrantes:**

- Joaquín Bermúdez Murcia
- Juan Felipe Hernández Montoya

**Tecnologías principales:** MongoDB Atlas · Python FastAPI · CLIP (OpenAI) · all-MiniLM-L6-v2 · Groq LLM · RAGAS 0.4.x
