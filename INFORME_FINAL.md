# Informe Final - Sistema RAG Inmobiliario con MongoDB NoSQL

## Bases de Datos No Relacionales - Proyecto Final

---

## 1. Resumen Ejecutivo

Este proyecto implementa un sistema **RAG** (Retrieval-Augmented Generation) para el dominio inmobiliario de Manizales, Colombia, utilizando **MongoDB Atlas** como base de datos NoSQL principal. El sistema integra búsqueda semántica multimodal (texto e imagenes) con un LLM gratuito (Groq + Llama 3.1) para responder preguntas complejas sobre propiedades, contratos y documentos legales.

El sistema almacena y procesa **100 documentos de texto** y **60 imagenes asociadas a 20 propiedades**, utilizando tres estrategias de chunking (fixed-size, sentence-aware, semantico) para determinar el impacto de la fragmentacion en la calidad de las respuestas RAG.

---

## 2. Arquitectura Tecnica Implementada

### 2.1 Diagrama de Arquitectura

```
[Frontend HTML/JS] ---> [API FastAPI (Python)] ---> [MongoDB Atlas]
                                      |
                                      v
                                 [Groq API (Llama 3.1)]
```

### 2.2 Componentes del Sistema

| Componente        | Tecnologia                                       | Proposito                                            |
| ----------------- | ------------------------------------------------ | ---------------------------------------------------- |
| Base de Datos     | MongoDB Atlas M0 (512 MB)                        | Almacenamiento NoSQL + Vector Search                 |
| API               | Python FastAPI                                   | Endpoints REST para busqueda y RAG                   |
| Frontend          | HTML + CSS + JavaScript vanilla                  | Interfaz de usuario monolitica (SPA)                 |
| Embeddings Texto  | sentence-transformers/all-MiniLM-L6-v2 (384 dim) | Busqueda semantica texto a texto                     |
| Embeddings Imagen | openai/clip-vit-base-patch32 (512 dim)           | Busqueda multimodal texto a imagen e imagen a imagen |
| LLM               | Groq API + Llama 3.1 (8B instant)                | Generacion de respuestas contextualizadas            |
| Chunking          | langchain + logica personalizada                 | 3 estrategias: fixed, sentence, semantic             |

### 2.3 Estrategia de Modelado NoSQL

Siguiendo las recomendaciones del documento del proyecto, se aplicaron tres estrategias de diseño:

**Embedded (datos incrustados):**

- Ratings y scores calculados se almacenan directamente en el documento de propiedad
- Historial de consultas del usuario como subdocumentos
- Metadatos pequenos como ubicacion y caracteristicas van dentro de la propiedad

**Referenced (referencias entre colecciones):**

- Las imagenes (media_assets) referencian a propiedades mediante `property_id`
- Los usuarios referencian agencias mediante `agency_id`
- Los chunks referencian documentos fuente mediante `doc_id`
- Los contratos referencian propiedades y usuarios involucrados

**Hibrido (mixto):**

- El documento principal de propiedad tiene `media_ids` como arreglo de referencias
- Pero los embeddings de metadatos se almacenan junto al chunk
- Las listas de media_ids permiten consultas eficientes sin cargar las imagenes completas

---

## 3. Colecciones MongoDB (14 colecciones)

| #   | Coleccion              | Proposito                                                   | Documentos           |
| --- | ---------------------- | ----------------------------------------------------------- | -------------------- |
| 1   | `users`                | Usuarios del sistema (propietarios, agentes, arrendatarios) | 13                   |
| 2   | `agencies`             | Agencias inmobiliarias                                      | 3                    |
| 3   | `properties`           | Propiedades con datos estructurados y coordenadas GeoJSON   | 20                   |
| 4   | `media_assets`         | URLs de imagenes reales de Unsplash por propiedad           | 60                   |
| 5   | `listings`             | Publicaciones de venta o arriendo                           | 20                   |
| 6   | `contracts`            | Contratos con clausulas y fechas                            | 15                   |
| 7   | `reviews`              | Resenas de propiedades por arrendatarios                    | 20                   |
| 8   | `maintenance_requests` | Solicitudes de mantenimiento                                | 10                   |
| 9   | `documents_repository` | Documentos fuente del dominio inmobiliario                  | 100                  |
| 10  | `document_chunks`      | Chunks de texto vectorizados con MiniLM                     | ~900 (3 estrategias) |
| 11  | `image_embeddings`     | Embeddings de imagen generados con CLIP                     | 60                   |
| 12  | `rag_queries_logs`     | Registro de consultas realizadas al sistema                 | Variables            |
| 13  | `rag_evaluations`      | Evaluaciones y respuestas guardadas                         | Variables            |
| 14  | `chat_sessions`        | Sesiones de chat (planeado)                                 | 15                   |

### 3.1 Ejemplo de Documento: Properties

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

### 3.2 Ejemplo de Documento: Document Chunks

```json
{
  "_id": "...",
  "doc_id": "doc_001",
  "texto": "El contrato de arrendamiento establece...",
  "estrategia_chunking": "semantic",
  "chunk_index": 2,
  "embedding": [0.023, -0.015, ...],
  "chunk_metadata": { "tipo_doc": "contrato", "fuente": "legal" }
}
```

### 3.3 Schema Validation

Se implementaron reglas de validacion en MongoDB para:

- `properties`: `_id` obligatorio con formato `prop_XXX`, `ubicacion.geo` debe ser Point valido
- `media_assets`: `url` debe ser string, `tipo` debe ser uno de los valores permitidos
- `document_chunks`: `embedding` debe ser arreglo de 384 floats, `estrategia_chunking` debe ser fixed_size, sentence o semantic

---

## 4. Indices Implementados

### 4.1 Indices Normales

| Coleccion         | Indice                             | Tipo        |
| ----------------- | ---------------------------------- | ----------- |
| `document_chunks` | `{ doc_id: 1 }`                    | Simple      |
| `document_chunks` | `{ estrategia_chunking: 1 }`       | Simple      |
| `document_chunks` | `{ "chunk_metadata.tipo_doc": 1 }` | Simple      |
| `properties`      | `{ "ubicacion.geo": "2dsphere" }`  | Geoespacial |
| `media_assets`    | `{ property_id: 1 }`               | Simple      |

### 4.2 Indices Vectoriales (Atlas Vector Search)

| Nombre Indice         | Coleccion          | Campo       | Dimensiones  | Similitud |
| --------------------- | ------------------ | ----------- | ------------ | --------- |
| `vector_index_chunks` | `document_chunks`  | `embedding` | 384 (MiniLM) | cosine    |
| `vector_index_images` | `image_embeddings` | `embedding` | 512 (CLIP)   | cosine    |

Ambos indices se crearon manualmente desde la interfaz de Atlas (Atlas Search → Create Search Index → JSON Editor).

---

## 5. Estrategias de Chunking

### 5.1 Fixed-Size

Divide el texto en fragmentos de tamano fijo (1024 caracteres, ~256 tokens) con superposicion de 128 caracteres (~32 tokens).

**Cuando usar:** Textos homogeneos, documentos sin estructura semantica clara.

### 5.2 Sentence-Aware

Respeta los limites de oraciones usando regex para espanol. Agrupa hasta 5 oraciones por chunk con superposicion de 1 oracion.

**Cuando usar:** Textos narrativos, descripciones de propiedades, noticias.

### 5.3 Semantic

Agrupa oraciones por similitud semantica usando embeddings de MiniLM. Umbral de coseno: 0.80. Cuando la similitud entre oraciones adyacentes cae por debajo del umbral, comienza un nuevo chunk.

**Cuando usar:** Documentos tecnicos, contratos legales, textos con cambios de tema.

---

## 6. Resultados del Experimento de Chunking

### 6.1 Metodologia

Se ejecutaron **10 consultas de prueba** sobre las 3 estrategias de chunking. Para cada consulta se midio:

- Cantidad de chunks recuperados
- Longitud promedio de los chunks en caracteres
- Score promedio de similitud coseno
- Tiempo de respuesta

Las consultas fueron seleccionadas para cubrir los tipos de preguntas mas comunes en el dominio inmobiliario:

| #   | Consulta                                          | Categoria               |
| --- | ------------------------------------------------- | ----------------------- |
| 1   | "Se permiten mascotas en el apartamento?"         | Reglas y politicas      |
| 2   | "Cual es el valor del arriendo mensual?"          | Costos y precios        |
| 3   | "Que incluye el contrato de arrendamiento?"       | Documentos legales      |
| 4   | "Cuantas habitaciones tiene la propiedad?"        | Caracteristicas fisicas |
| 5   | "Que servicios publicos estan incluidos?"         | Servicios               |
| 6   | "Cual es la politica de mascotas en el edificio?" | Reglamentos             |
| 7   | "Como se calcula la administracion?"              | Costos recurrentes      |
| 8   | "Que documentos se necesitan para arrendar?"      | Tramites                |
| 9   | "Hay parqueadero disponible?"                     | Amenidades              |
| 10  | "Cual es el procedimiento para mantenimiento?"    | Soporte                 |

### 6.2 Resultados Cuantitativos

A continuacion se presentan los resultados obtenidos al ejecutar las 10 consultas sobre las 3 estrategias:

| Consulta                        | Fixed-Size (score) | Sentence (score) | Semantic (score) | Ganadora |
| ------------------------------- | ------------------ | ---------------- | ---------------- | -------- |
| Se permiten mascotas?           | 0.8467             | 0.8522           | **0.8872**       | Semantic |
| Valor del arriendo mensual?     | 0.7627             | 0.7580           | **0.7985**       | Semantic |
| Cuantas habitaciones tiene?     | 0.7601             | 0.7759           | **0.8141**       | Semantic |
| Que incluye el contrato?        | 0.8350             | 0.8380           | **0.8592**       | Semantic |
| Ubicacion exacta del inmueble?  | 0.7742             | 0.7766           | **0.8159**       | Semantic |
| Servicios publicos incluidos?   | 0.8153             | 0.8265           | **0.8724**       | Semantic |
| Restricciones para subarrendar? | 0.7725             | 0.7725           | **0.7966**       | Semantic |
| Condiciones del pago del canon? | 0.7944             | 0.8169           | **0.8497**       | Semantic |
| Como es la cocina?              | 0.7954             | 0.7398           | **0.8100**       | Semantic |
| Opiniones de otros usuarios?    | 0.7476             | 0.7649           | **0.7816**       | Semantic |

**Resumen global por estrategia:**

| Metrica                   | Fixed-Size | Sentence | Semantic   |
| ------------------------- | ---------- | -------- | ---------- |
| Total chunks en BD        | 412        | 561      | 2143       |
| Longitud promedio (chars) | 777.8      | 481.5    | 237.2      |
| Score promedio global     | 0.7904     | 0.7921   | **0.8285** |
| Consultas ganadas         | 0          | 0        | 10 de 10   |

### 6.3 Interpretacion de Resultados

La estrategia **semantica** gano las 10 consultas con un score promedio de **0.8285**, superando a sentence (0.7921) y fixed-size (0.7904). Esto se debe a que el chunking semantico agrupa oraciones por tema, produciendo chunks tematicamente coherentes que el `$vectorSearch` puede emparejar mejor con la intencion de la consulta.

Sin embargo, la estrategia semantica produce chunks mucho mas cortos (237 caracteres promedio vs 778 de fixed-size) porque los documentos inmobiliarios cambian frecuentemente de tema. Esto significa que se necesitan mas chunks para cubrir la misma informacion. La estrategia **sentence** ofrece el mejor equilibrio: chunks coherentes (481 caracteres) con buena puntuacion (0.7921) y la mitad de chunks que semantic.

### 6.4 Conclusion

Para el dominio inmobiliario, la estrategia **semantica** ofrece la mejor precision de busqueda, pero la estrategia **sentence** es la mas equilibrada en terminos de cobertura vs calidad. Se recomienda un enfoque hibrido: usar semantic para documentos legales (contratos, reglamentos) donde cada clausula es un tema distinto, y sentence para descripciones de propiedades y chats donde las oraciones completas son mas informativas. La estrategia fixed-size queda como opcion rapida para ingesta inicial por su simplicidad computacional.

---

## 7. Resultados y Evaluacion del Sistema

### 7.1 Evaluacion de Busqueda Semantica (texto-texto)

Para evaluar la calidad de la busqueda semantica, se realizaron pruebas con consultas de diferentes categorias:

| Consulta                        | Estrategia optima | Score promedio | Observacion                                    |
| ------------------------------- | ----------------- | -------------- | ---------------------------------------------- |
| "Se permiten mascotas?"         | semantic          | 0.8872         | Encontro chunks del FAQ y reglamentos          |
| "Valor del arriendo?"           | semantic          | 0.7985         | Chunks de contratos con clausulas de canon     |
| "Cuantas habitaciones?"         | semantic          | 0.8141         | Descripciones de propiedades con datos exactos |
| "Que incluye el contrato?"      | semantic          | 0.8592         | Agrupo multiples clausulas del mismo tema      |
| "Servicios publicos incluidos?" | semantic          | 0.8724         | Chunks de FAQ sobre servicios                  |

**Conclusion:** El sistema recupera consistentemente los chunks relevantes para preguntas del dominio inmobiliario. La estrategia optima depende del tipo de pregunta: semantica para preguntas conceptuales, sentence para datos concretos.

### 7.2 Evaluacion de Busqueda Multimodal

**Imagen a imagen:** Se probo con imagenes de fachada como referencia. El sistema retorno otras fachadas visualmente similares con scores altos, demostrando que los embeddings CLIP generados con openai/clip-vit-base-patch32 capturan correctamente las caracteristicas visuales de las imagenes.

**Texto a imagen:** Consultas como "fachada moderna" retornaron predominantemente imagenes de tipo `imagen_fachada`, mientras que "sala amplia" retorno imagenes de tipo `imagen_sala`, confirmando que CLIP alinea correctamente los espacios vectoriales de texto e imagen.

**Imagen a texto via RAG:** Al seleccionar una imagen en la galeria, el sistema permite identificar su propiedad asociada y realizar consultas RAG sobre los documentos relacionados, cerrando el ciclo multimodal completo.

### 7.3 Evaluacion del Pipeline RAG

El pipeline RAG completo se evaluo cualitativamente:

- **Relevancia del contexto:** Los 5 chunks recuperados siempre incluyen informacion pertinente a la pregunta
- **Calidad de la respuesta:** El LLM genera respuestas coherentes basadas exclusivamente en el contexto
- **Tiempo de respuesta:** ~5 segundos promedio (busqueda + generacion con Groq)
- **Trazabilidad:** Cada consulta queda registrada en `rag_queries_logs` con su embedding, chunks usados y respuesta generada

---

## 8. API REST - Endpoints Documentados

| Metodo | Ruta                    | Proposito                      | Request                        | Response                              |
| ------ | ----------------------- | ------------------------------ | ------------------------------ | ------------------------------------- |
| GET    | `/`                     | Health check                   | -                              | `{ "status": "ok", "db": "..." }`     |
| POST   | `/search`               | Busqueda vectorial texto-texto | `{ query, top_k, estrategia }` | `{ resultados, total }`               |
| POST   | `/rag`                  | Pipeline RAG completo          | `{ query, top_k, estrategia }` | `{ respuesta, contexto, chunks }`     |
| POST   | `/search/image`         | Busqueda imagen-imagen         | `{ media_id, top_k }`          | `{ media_id_referencia, resultados }` |
| GET    | `/search/image/random`  | Galeria aleatoria              | `top_k`                        | `{ resultados }`                      |
| POST   | `/search/text-to-image` | Busqueda texto-imagen          | `{ query, top_k }`             | `{ resultados }`                      |
| GET    | `/chunks/compare`       | Comparar estrategias           | `{ query, top_k }`             | `{ fixed, sentence, semantic }`       |
| GET    | `/experiment/results`   | Resultados experimento         | `top_k`                        | `{ estrategias, consultas, scores }`  |
| GET    | `/stats`                | Estadisticas del sistema       | -                              | `{ colecciones, totales }`            |
| GET    | `/evaluations`          | Evaluaciones guardadas         | `limit`                        | `{ evaluaciones }`                    |

---

## 9. Pipeline Multimodal

### 9.1 Texto a Texto

```
consulta del usuario
       |
       v
all-MiniLM-L6-v2 (embedding 384d)
       |
       v
$vectorSearch en document_chunks (indice: vector_index_chunks)
       |
       v
top-k chunks recuperados + construccion de contexto
       |
       v
LLM (Groq + Llama 3.1) genera respuesta basada en el contexto
       |
       v
respuesta final al usuario
```

### 9.2 Texto a Imagen

```
descripcion textual del usuario (ej: "fachada moderna")
       |
       v
CLIP text encoder (embedding 512d)
       |
       v
$vectorSearch en image_embeddings (indice: vector_index_images)
       |
       v
imagenes visualmente similares
```

### 9.3 Imagen a Imagen

```
imagen de referencia
       |
       v
CLIP vision encoder (embedding 512d)
       |
       v
$vectorSearch en image_embeddings (indice: vector_index_images)
       |
       v
imagenes visualmente similares
```

---

## 10. Lecciones Aprendidas y Recomendaciones

### 10.1 Lecciones Aprendidas

1. **El chunking afecta directamente la calidad RAG**: La estrategia de chunking es la decision mas importante en un sistema RAG. Una mala fragmentacion produce contexto insuficiente o ruidoso.

2. **CLIP requiere hardware**: Generar embeddings de imagen con CLIP en CPU toma ~40 segundos para 60 imagenes. En produccion se recomienda GPU o un servicio de embeddings.

3. **MongoDB Atlas Vector Search es intuitivo**: La integracion de $vectorSearch con el Aggregation Framework permite hacer busquedas hibridas (vectorial + filtros tradicionales) en una sola consulta.

4. **Las URLs de imagenes deben ser persistentes**: Usar servicios como Unsplash garantiza que las URLs no expiren, a diferencia de CDN temporales.

5. **El modelo de datos hibrido fue adecuado**: Las referencias entre colecciones permiten actualizar imagenes sin modificar propiedades, y los embeddings incrustados en los chunks permiten busqueda eficiente.

### 10.2 Recomendaciones

1. **Implementar RAGAS**: Para una evaluacion objetiva de la calidad del sistema, se recomienda integrar el framework RAGAS con las metricas de faithfulness, answer relevancy y context recall.

2. **Agregar busqueda hibrida**: Combinar $vectorSearch con $search (texto completo) para mejorar la recuperacion en consultas con terminos exactos.

3. **Cache de embeddings**: Almacenar en memoria los embeddings mas consultados para reducir latencia.

4. **Pipeline de actualizacion**: Implementar triggers de Atlas que automaticen la re-vectorizacion cuando se agreguen nuevos documentos.

---

## 11. Comparacion con Enfoque Relacional

| Aspecto                | SQL (Relacional)                                 | MongoDB (NoSQL)                                            |
| ---------------------- | ------------------------------------------------ | ---------------------------------------------------------- |
| **Modelado**           | Esquema rigido con tablas normalizadas           | Esquema flexible, documentos embebidos o referenciados     |
| **Embeddings**         | Tabla separada con JOINs costosos                | Misma coleccion o coleccion dedicada con $lookup           |
| **Vector Search**      | No nativo, requiere extension externa (pgvector) | Nativo con Atlas Vector Search y $vectorSearch             |
| **Geoespacial**        | PostGIS (extension)                              | Nativo con GeoJSON e indices 2dsphere                      |
| **Escalabilidad**      | Vertical principalmente                          | Horizontal nativa (sharding)                               |
| **Consultas hibridas** | Multiples queries o funciones complejas          | Un solo pipeline de agregacion con $vectorSearch + filtros |
| **Schema Validation**  | Obligatorio (DDL)                                | Opcional, con validacion a nivel de documento              |
| **Flexibilidad**       | Cambios requieren migraciones                    | Cambios sin downtime, documentos con campos distintos      |

**Conclusion:** MongoDB ofrece ventajas significativas para sistemas RAG al integrar de forma nativa el almacenamiento de documentos, busqueda vectorial y consultas hibridas en una sola plataforma, sin necesidad de servicios externos ni migraciones de esquema.

---

## 12. Instrucciones de Instalacion y Ejecucion

```bash
# 1. Clonar repositorio
git clone <repo-url>
cd basesInmobiliaria

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con MONGODB_URI y GROQ_API_KEY

# 3. Instalar dependencias Python
pip install -r python/requirements.txt
pip install uvicorn

# 4. Generar dataset completo (datos + embeddings CLIP reales)
cd python
python generate_dataset.py

# 5. Ejecutar pipeline de chunking y embeddings de texto
python chunking_pipeline.py

# 6. Iniciar API
python -m uvicorn api.main:app --reload --port 8000

# 7. En otra terminal, iniciar frontend
cd ..
python -m http.server 3000

# 8. Abrir http://localhost:3000 en el navegador
```

---

## 13. Creditos

**Proyecto:** Sistema RAG NoSQL con MongoDB - Inmobiliaria Manizales

**Curso:** Bases de Datos No Relacionales

**Integrantes:**

- Joaquín Bermúdez Murcia
- Juan Felipe Hernández Montoya

**Tecnologias:** MongoDB Atlas, Python FastAPI, CLIP, MiniLM, Groq LLM
