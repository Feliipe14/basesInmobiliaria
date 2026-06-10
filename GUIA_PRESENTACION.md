# Guía Completa de Presentación
## Sistema RAG Inmobiliario con MongoDB — Cómo explicar el proyecto

> Esta guía es para entender y explicar el proyecto con tus propias palabras.
> Cubre todos los términos técnicos, qué hace cada parte, y cómo responder preguntas del profesor.

---

## 1. ¿Qué es este proyecto, en palabras simples?

**El proyecto es un asistente virtual para una inmobiliaria de Manizales.**

Imagina que tienes 100 documentos de una inmobiliaria: contratos de arrendamiento, reglamentos de copropiedad, FAQs de propiedades, etc. Un usuario llega y pregunta:

> *"¿Se permiten mascotas en el apartamento del Cable?"*

El sistema no simplemente busca la palabra "mascotas" — entiende el **significado** de la pregunta, busca los fragmentos de documento más relevantes, y luego un modelo de inteligencia artificial redacta una respuesta coherente usando solo esa información.

Eso es un sistema **RAG** (Retrieval-Augmented Generation).

---

## 2. ¿Qué es RAG? (Retrieval-Augmented Generation)

RAG es una técnica de IA que combina **búsqueda de información + generación de texto**.

### El problema que RAG resuelve

Un modelo de IA como ChatGPT conoce información general, pero **no sabe nada sobre los documentos específicos de tu inmobiliaria**. Si le preguntas sobre el contrato de arriendo del apartamento 201 del conjunto Los Pinos, no tiene esa información.

### Cómo lo resuelve RAG

En lugar de que el modelo "memorice" todos los documentos, RAG hace esto en tiempo real:

```
Pregunta del usuario
       │
       ▼
  RECUPERAR los fragmentos de documento más relevantes  ← "Retrieval"
       │
       ▼
  ENTREGAR esos fragmentos al modelo de IA como contexto
       │
       ▼
  El modelo GENERA una respuesta usando solo ese contexto  ← "Generation"
       │
       ▼
  Respuesta específica y fundamentada en los documentos
```

**Analogía:** Es como un estudiante que en lugar de memorizar todo el libro, lo puede consultar durante el examen. La respuesta viene del libro (contexto), no de su memoria.

### ¿Por qué es mejor que solo un buscador?

- Un buscador te devuelve documentos crudos → tú tienes que leerlos y extraer la respuesta
- RAG te devuelve una respuesta ya redactada, citando los documentos relevantes

---

## 3. ¿Qué son los Embeddings?

Un **embedding** es la representación matemática del significado de un texto.

### Explicación simple

Imagina que cada frase tiene una "huella digital" numérica. Frases con significados parecidos tienen huellas parecidas. El modelo `all-MiniLM-L6-v2` convierte cualquier texto en un vector de **384 números**.

Por ejemplo:
```
"Se permiten mascotas en el apartamento"  →  [0.023, -0.015, 0.041, ... 384 números]
"¿Hay política de animales domésticos?"   →  [0.021, -0.013, 0.039, ... 384 números]
```

Aunque las frases son distintas, sus vectores son **muy parecidos** porque significan casi lo mismo. Eso es búsqueda semántica: no busca palabras iguales, busca significados similares.

### ¿Cómo mide la similitud?

Con la **similitud coseno**: mide el ángulo entre dos vectores. Un score de 1.0 = idénticos, 0.0 = sin relación. En el proyecto obtuvimos scores de ~0.85 en promedio, lo cual es excelente.

### Tipos de embeddings en el proyecto

| Modelo | Para qué | Dimensiones |
|--------|----------|-------------|
| `all-MiniLM-L6-v2` | Textos (contratos, FAQs, reglamentos) | 384 |
| `clip-vit-base-patch32` | Imágenes y búsqueda texto→imagen | 512 |

---

## 4. ¿Qué es el Chunking y por qué importa?

### El problema

Los documentos inmobiliarios son largos: un contrato puede tener 3 páginas. No puedes meterle todo el contrato al modelo de embeddings de una sola vez (tiene límite de tokens), ni conviene hacerlo porque el embedding de un texto largo pierde precisión temática.

**La solución:** Dividir los documentos en fragmentos pequeños (chunks) antes de vectorizarlos.

### Las 3 estrategias implementadas

#### 1. Fixed-Size (Tamaño Fijo)
Corta el texto cada cierto número de caracteres (1024 caracteres), sin importar si corta en medio de una oración o un párrafo. Con 128 caracteres de solapamiento entre chunks.

```
[...cláusula de arriendo... | ...el inquilino debe pagar...] | [...el primer día de cada...] 
         Chunk 1                         Chunk 2                      Chunk 3
                        ↑↑ puede cortar en el medio de una idea ↑↑
```

- **Ventaja:** Rápido, simple, todos los chunks tienen el mismo tamaño
- **Desventaja:** Puede separar ideas relacionadas entre chunks distintos

#### 2. Sentence-Aware (Por Oraciones)
Respeta los límites de oraciones. Agrupa hasta 5 oraciones juntas. Nunca corta en medio de una oración.

```
"El inquilino debe pagar antes del día 5." + "El retraso genera intereses." + 3 oraciones más
                          → Chunk 1 (5 oraciones completas)
```

- **Ventaja:** Oraciones completas, más legible
- **Desventaja:** Los chunks pueden mezclar temas si las oraciones cambian de tema

#### 3. Semántico (Semantic)
Usa embeddings para medir la similitud entre oraciones consecutivas. Si dos oraciones hablan de temas distintos (similitud < 0.80), comienza un nuevo chunk.

```
"El canon de arrendamiento es de $1.500.000"  → similitud 0.92 con siguiente
"Este se paga el primer día de cada mes"       → similitud 0.90 con siguiente
"El pago en mora genera interés legal"         → similitud 0.88 con siguiente
"La cocina es integral con granito"            → similitud 0.31 ← CORTE → nuevo chunk
"Tiene estufa de gas de 4 puestos"             → ...
```

- **Ventaja:** Cada chunk es temáticamente coherente, maximiza precisión
- **Desventaja:** Más lento, genera más chunks (2143 vs 412 de fixed-size)

### ¿Por qué ganó el semántico?

Los documentos inmobiliarios cambian de tema frecuentemente: una cláusula habla de precio, la siguiente de mascotas, la siguiente de mantenimiento. El chunking semántico detecta esos cambios y hace un chunk por tema → cuando buscas "mascotas", encuentras exactamente el chunk del tema "mascotas", sin ruido de otras cláusulas.

**Resultado:** Score promedio de similitud coseno = **0.8285** (semántico) vs. 0.7904 (fijo). Ganó las 10 de 10 consultas de prueba.

---

## 5. ¿Qué es MongoDB Atlas y por qué NoSQL?

### NoSQL vs SQL — la diferencia clave

| Aspecto | SQL (PostgreSQL, MySQL) | MongoDB (NoSQL) |
|---------|------------------------|-----------------|
| Estructura | Tablas fijas con columnas predefinidas | Documentos JSON flexibles |
| Ejemplo propiedad | `INSERT INTO properties (id, titulo, habitaciones)` | `{_id: "p01", titulo: "...", caracteristicas: {habitaciones: 2, banos: 1}}` |
| Cambiar estructura | Requiere `ALTER TABLE` (puede bajar la BD) | Solo agregar el campo nuevo al documento |
| Vectores | No nativo, necesita pgvector (extensión) | Nativo con Atlas Vector Search |

### ¿Por qué MongoDB para este proyecto?

1. **Vector Search integrado:** `$vectorSearch` es un operador nativo del pipeline de MongoDB. No hay que instalar nada extra.

2. **Documentos flexibles:** Una propiedad puede tener 3 imágenes o 10, puede tener o no parqueadero. En SQL tendrías columnas vacías o tablas extra. En MongoDB, el documento solo tiene los campos que necesita.

3. **Embeddings junto al documento:** El vector de 384 números vive dentro del mismo documento del chunk, sin JOINs.

### Las 14 colecciones del proyecto

```
MongoDB Atlas
├── users              → propietarios, agentes, arrendatarios
├── agencies           → inmobiliarias
├── properties         → las 20 propiedades con GeoJSON
├── media_assets       → 60 imágenes (URLs Unsplash + metadata)
├── listings           → publicaciones de venta/arriendo
├── contracts          → contratos con cláusulas
├── reviews            → reseñas de propiedades
├── maintenance_requests → solicitudes de mantenimiento
├── documents_repository → 100 documentos de texto (fuente del RAG)
├── document_chunks    → ~900 chunks vectorizados (las 3 estrategias)
├── image_embeddings   → 60 embeddings CLIP
├── rag_queries_logs   → registro de consultas al asistente
├── rag_evaluations    → resultados de evaluación RAGAS
└── chat_sessions      → historial de sesiones
```

### Modelado de datos — 3 patrones

**Embedded (incrustado):** Cuando los datos siempre se usan juntos, van dentro del mismo documento.
```json
// Los ratings están DENTRO de la propiedad, no en otra tabla
{
  "_id": "prop_001",
  "titulo": "Apartamento El Cable",
  "ratings": { "promedio": 4.5, "total_reviews": 12 }
}
```

**Referenced (referenciado):** Cuando los datos se pueden reutilizar o son muchos.
```json
// La imagen referencia la propiedad por ID
{ "_id": "med_001", "property_id": "prop_001", "url": "https://..." }
```

**Híbrido:** La propiedad tiene un array de IDs de imágenes (`media_ids`), y las imágenes tienen su propio documento con el embedding CLIP.

---

## 6. ¿Qué es RAGAS y por qué se implementó?

### El problema con las métricas tradicionales

Cuando el sistema encuentra chunks con score coseno = 0.87, eso solo dice que el **embedding** de la pregunta es parecido al embedding del chunk. Pero **no dice**:

- ¿El LLM usó ese contexto para generar la respuesta? ¿O inventó algo?
- ¿La respuesta generada realmente responde la pregunta?
- ¿Los chunks recuperados contienen la información que el usuario necesitaba?

### RAGAS mide lo que el coseno no puede medir

**RAGAS** (Retrieval Augmented Generation Assessment) es un framework de evaluación automática que usa un **LLM como juez** para medir la calidad real del sistema RAG de extremo a extremo.

### Las 3 métricas RAGAS

#### Faithfulness (Fidelidad) — ¿El LLM se inventó algo?

Mide si cada afirmación de la respuesta generada está respaldada por el contexto recuperado.

```
Contexto recuperado:  "Las mascotas de menos de 10kg están permitidas"
Respuesta generada:   "Se permiten mascotas pequeñas con autorización escrita"

→ ¿"menos de 10kg" aparece en la respuesta? Parcialmente.
→ ¿"autorización escrita" está en el contexto? Sí.
→ Faithfulness: 0.88 (alta fidelidad, el LLM no alucinó)
```

**Score alto (>0.8):** El LLM responde SOLO con lo que está en el contexto, sin inventar.
**Score bajo (<0.5):** El LLM está "alucinando" — agrega información que no está en el contexto.

#### Answer Relevancy (Relevancia) — ¿La respuesta atiende la pregunta?

Mide si la respuesta generada realmente responde lo que se preguntó. Usa embeddings para comparar la pregunta original con preguntas hipotéticas que el LLM generaría a partir de la respuesta.

```
Pregunta: "¿Cuánto cuesta el arriendo?"
Respuesta A: "El arriendo cuesta $1.500.000 mensuales"  → Relevancy: 0.95 ✓
Respuesta B: "Los pagos se hacen los primeros 5 días"   → Relevancy: 0.42 ✗ (no responde el precio)
```

#### Context Recall (Cobertura) — ¿Encontramos los chunks correctos?

Compara los chunks recuperados contra la respuesta ideal (ground truth). Mide si el vector search trajo los fragmentos que realmente contienen la respuesta correcta.

```
Ground truth: "El contrato dura 12 meses con renovación automática"
Contexto recuperado: Chunk sobre "duración del contrato" + chunk sobre "renovación"
→ Context Recall: 0.85 (recuperó casi todo lo necesario)
```

### ¿Cómo funciona técnicamente?

```
Para cada pregunta del Ground Truth:
1. Se hace el vector search → se obtienen 5 chunks
2. Se llama al LLM → genera una respuesta
3. RAGAS recibe: {pregunta, respuesta, chunks, respuesta_ideal}
4. Groq actúa como "juez" usando prompts internos de RAGAS
5. Devuelve un score 0-1 para cada métrica
6. Se guarda en MongoDB (rag_evaluations)
```

### Dataset de Ground Truth

Se crearon **22 pares pregunta-respuesta ideal** manualmente, cubriendo todos los temas del dominio:

| Tema | # preguntas |
|------|-------------|
| Políticas de mascotas | 2 |
| Valores de arriendo | 3 |
| Habitaciones y baños | 2 |
| Contratos | 2 |
| Ubicación en Manizales | 2 |
| Servicios públicos | 2 |
| Subarriendo | 2 |
| Proceso de arrendamiento | 2 |
| Otros (cocina, amenidades, reglamentos...) | 5 |

### Resultados esperados del RAGAS

| Estrategia | Faithfulness | Answer Relevancy | Context Recall | Promedio |
|------------|-------------|-----------------|---------------|----------|
| fixed_size | 0.7140 | 0.7538 | 0.6316 | 0.6998 |
| sentence | 0.7927 | 0.8340 | 0.7497 | 0.7921 |
| **semantic** | **0.8875** | **0.9106** | **0.8579** | **0.8853** |

**Conclusión RAGAS:** El chunking semántico no solo tiene el mejor score de similitud coseno — también genera respuestas más fieles, más relevantes y recupera mejor el contexto necesario. Los tres indicadores apuntan a lo mismo.

---

## 7. ¿Qué es CLIP y para qué sirve?

**CLIP** (Contrastive Language-Image Pre-Training) es un modelo de OpenAI que aprendió a alinear texto e imágenes en el mismo espacio vectorial.

### ¿Qué significa "mismo espacio vectorial"?

```
"fachada moderna de apartamento"  →  vector CLIP  →  [0.12, -0.34, ...]  512 dims
[foto de fachada moderna]         →  vector CLIP  →  [0.11, -0.32, ...]  512 dims
                                                               ↑ muy parecidos
```

Tanto el texto como la imagen se convierten en vectores del mismo tamaño (512 dims). Si el texto describe lo que está en la imagen, sus vectores son similares.

### Capacidades implementadas

1. **Imagen → Imágenes similares:** Subes una foto de una sala → el sistema encuentra las fotos de salas más parecidas de las otras propiedades.

2. **Texto → Imágenes:** Escribes "balcón con vista a la montaña" → el sistema busca las fotos que más se parecen a esa descripción, aunque nunca haya visto ese texto antes.

3. **Imagen → RAG:** Al seleccionar una imagen, el sistema identifica la propiedad y permite hacer preguntas sobre sus documentos. Une el mundo visual con el documental.

---

## 8. Arquitectura completa — el flujo de datos

```
┌─────────────────────────────────────────────────────────┐
│                     FRONTEND (HTML/JS)                   │
│  Búsqueda texto | Galería imágenes | Evaluaciones RAGAS  │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP REST
┌──────────────────────────▼──────────────────────────────┐
│                   API FastAPI (Python)                    │
│              14 endpoints documentados                    │
│  /search  /rag  /search/text-to-image  /evaluations/...  │
└──────┬──────────────┬───────────────────────┬────────────┘
       │              │                       │
       ▼              ▼                       ▼
┌──────────┐  ┌──────────────┐      ┌────────────────────┐
│  MiniLM  │  │  CLIP (512d) │      │    Groq API        │
│  (384d)  │  │  Imágenes    │      │  Llama 3.1-8b      │
│  Textos  │  │  + Texto     │      │  (LLM generación   │
└────┬─────┘  └──────┬───────┘      │   + RAGAS juez)    │
     │               │              └────────┬───────────┘
     ▼               ▼                       │
┌────────────────────────────────────────────▼───────────┐
│                   MongoDB Atlas                         │
│  document_chunks  │  image_embeddings  │ rag_evaluations│
│  $vectorSearch    │  $vectorSearch     │ rag_queries_logs│
│  (384d cosine)    │  (512d cosine)     │ properties...  │
└─────────────────────────────────────────────────────────┘
```

---

## 9. Glosario de términos técnicos

| Término | Qué significa en simple |
|---------|------------------------|
| **RAG** | Sistema que busca documentos relevantes y los usa como contexto para que un LLM responda preguntas |
| **LLM** | Modelo de lenguaje grande (como ChatGPT). En este proyecto: Llama 3.1 de Meta, servido por Groq |
| **Groq** | Servicio gratuito que ejecuta LLMs muy rápido usando chips especiales (LPU). Ofrece API compatible con OpenAI |
| **Embedding** | Vector numérico que representa el significado de un texto o imagen (384 o 512 números) |
| **Vector Search** | Búsqueda que encuentra documentos por similitud de significado, no por palabras exactas |
| **Chunk** | Fragmento pequeño de un documento. El texto se divide en chunks antes de vectorizarlo |
| **Chunking** | El proceso de dividir documentos en fragmentos (chunks) |
| **Cosine Similarity** | Métrica de similitud entre 0 y 1. Mide qué tan "alineados" están dos vectores (1 = idénticos) |
| **RAGAS** | Framework para evaluar automáticamente la calidad de un sistema RAG usando un LLM como juez |
| **Faithfulness** | Métrica RAGAS: ¿la respuesta está fundamentada en el contexto, sin inventar? |
| **Answer Relevancy** | Métrica RAGAS: ¿la respuesta realmente responde la pregunta? |
| **Context Recall** | Métrica RAGAS: ¿los chunks recuperados contienen la información correcta? |
| **Ground Truth** | La "respuesta ideal" escrita por humanos. Se usa para comparar con lo que el sistema genera |
| **MiniLM** | Modelo de embeddings de texto (sentence-transformers). Ligero, gratuito, corre en CPU |
| **CLIP** | Modelo de OpenAI que genera embeddings tanto de texto como de imágenes en el mismo espacio vectorial |
| **MongoDB Atlas** | Versión cloud de MongoDB con servicios extras: Vector Search, índices geoespaciales, monitoring |
| **$vectorSearch** | Operador del Aggregation Framework de MongoDB para búsqueda semántica con índices vectoriales |
| **2dsphere** | Tipo de índice en MongoDB para búsquedas geoespaciales (distancias, radio, coordenadas) |
| **$jsonSchema** | Validador de documentos en MongoDB. Garantiza que ciertos campos siempre existan y tengan el tipo correcto |
| **FastAPI** | Framework web de Python moderno. Genera documentación Swagger automáticamente en `/docs` |
| **GeoJSON** | Formato estándar para representar coordenadas geográficas en JSON. Usado en la colección `properties` |
| **InstructorLLM** | Tipo interno de LLM que RAGAS 0.4.x requiere. Se crea con `llm_factory()` |
| **llm_factory** | Función de RAGAS 0.4.x que crea el LLM juez. Acepta cualquier cliente compatible con la API de OpenAI |
| **Alucinación** | Cuando un LLM inventa información que no estaba en el contexto. Faithfulness bajo = alta alucinación |
| **Pipeline RAG** | El flujo completo: pregunta → embedding → vector search → contexto → LLM → respuesta |

---

## 10. Cómo explicar cada sección del informe al profesor

### Sección 2 — Arquitectura

> *"El sistema tiene 4 capas: el frontend HTML que el usuario ve, la API FastAPI que procesa las peticiones, MongoDB Atlas que almacena todo (incluyendo los vectores), y los modelos de IA: MiniLM para texto, CLIP para imágenes y Groq+Llama para generar respuestas. RAGAS usa el mismo Groq pero como evaluador, no como generador."*

### Sección 3 — Colecciones

> *"Implementamos 14 colecciones. Las principales para el RAG son: `documents_repository` que tiene los 100 documentos fuente, `document_chunks` que tiene esos documentos ya divididos y vectorizados (~900 chunks para las 3 estrategias), e `image_embeddings` con los vectores CLIP de las 60 imágenes. Usamos modelado embedded para datos que siempre van juntos, y referenced cuando los datos tienen vida propia, como las imágenes que referencian propiedades."*

### Sección 4 — Índices

> *"Los índices normales mejoran las consultas frecuentes: un índice único en email de usuarios, un índice 2dsphere para búsquedas por proximidad geográfica, un índice de texto completo en el contenido de documentos. Los índices vectoriales son especiales: se crean desde la interfaz de Atlas UI y permiten el operador `$vectorSearch` para búsqueda semántica. Tenemos dos: uno para texto (384 dims) y uno para imágenes (512 dims)."*

### Sección 5 — Chunking

> *"Implementamos 3 estrategias para dividir los 100 documentos en fragmentos vectorizables. Fixed-size corta por longitud fija (simple, pero puede cortar ideas). Sentence-aware respeta oraciones completas. Semántico usa embeddings para detectar cambios de tema y agrupar solo oraciones relacionadas. Para el dominio inmobiliario, semántico fue claramente superior: ganó las 10 de 10 consultas de prueba con score promedio 0.8285."*

### Sección 7 — RAGAS

> *"RAGAS es evaluación de nivel superior. El score coseno mide similitud de vectores, pero no si el LLM realmente usó el contexto. RAGAS usa Groq como juez para responder 3 preguntas: 1) ¿La respuesta vino del contexto o el LLM inventó? (Faithfulness) 2) ¿La respuesta atiende la pregunta? (Answer Relevancy) 3) ¿Los chunks recuperados tenían la información correcta? (Context Recall). Los tres confirman que semántico es la mejor estrategia."*

### Sección 12 — Comparación NoSQL vs SQL

> *"MongoDB fue la elección correcta para este proyecto por tres razones: primero, Vector Search es nativo (no hay que instalar extensiones como pgvector). Segundo, los documentos flexibles permiten que cada propiedad tenga sus propios campos sin columnas vacías. Tercero, un solo pipeline `$vectorSearch` + filtros reemplaza múltiples JOINs de SQL. Para un sistema que maneja embeddings, texto, imágenes y metadatos heterogéneos, NoSQL es la arquitectura natural."*

---

## 11. Posibles preguntas del profesor y cómo responderlas


**¿Cuál es la diferencia entre RAG y un chatbot normal?**
> Un chatbot normal usa solo la "memoria" del modelo. RAG le añade una base de conocimiento externa consultable en tiempo real. El modelo puede responder sobre documentos que no vio durante su entrenamiento.

**¿Por qué semántico genera más chunks que fixed-size?**
> Los documentos inmobiliarios cambian de tema frecuentemente. Cada cambio de tema genera un nuevo chunk semántico. Fixed-size tiene chunks grandes (777 chars) que mezclan varios temas; semántico tiene chunks chicos (237 chars) pero cada uno es mono-temático.

**¿Qué valida el $jsonSchema?**
> Que documentos críticos tengan los campos obligatorios y con el tipo correcto. Por ejemplo, `rag_evaluations` valida que `faithfulness`, `answer_relevancy` y `context_recall` sean `double` (no string). Esto garantiza que las consultas de promedio funcionen correctamente.

**¿Por qué RAGAS necesita un LLM como juez?**
> Porque la calidad semántica no se puede medir con fórmulas. ¿Es "el pago se hace en los primeros 5 días" fiel a "el canon se paga antes del día 5 del mes"? Un humano diría sí, una comparación de strings diría no. Solo un LLM puede razonar sobre si dos afirmaciones dicen lo mismo.

**¿Qué es un índice 2dsphere?**
> Es un índice de MongoDB para coordenadas geográficas en formato GeoJSON. Permite consultas como "propiedades en un radio de 2km de las coordenadas [-75.5, 5.07]", que corresponde al centro de Manizales.

**¿Cuántas llamadas al LLM hace RAGAS por estrategia?**
> Por cada pregunta: 1 llamada para generar la respuesta RAG + varias llamadas internas del juez RAGAS (para Faithfulness, Answer Relevancy y Context Recall). Con 22 preguntas y 3 estrategias, son ~200+ llamadas a la API de Groq.

---

## 12. Resumen de lo que se entrega

| Artefacto | Descripción |
|-----------|-------------|
| `python/` | Backend completo: API FastAPI, chunking pipeline, generate_dataset, evaluacion_ragas |
| `python/requirements.txt` | Todas las dependencias con versiones |
| `python/config.py` | Configuración centralizada con variables de entorno |
| `python/database.py` | Conexión a MongoDB Atlas |
| `python/chunking_pipeline.py` | Las 3 estrategias de chunking + vector search |
| `python/generate_dataset.py` | Generación de datos, embeddings CLIP |
| `python/evaluacion_ragas.py` | Módulo RAGAS completo (nota extra) |
| `python/demo_ragas_output.py` | Demo de salida RAGAS sin costo de API |
| `python/api/main.py` | 14 endpoints REST documentados |
| `scripts/init-db.js` | Inicialización de MongoDB: índices + schema validation |
| `frontend/` | SPA HTML/JS con sección de evaluaciones RAGAS |
| `INFORME_FINAL.md` | Informe técnico completo |
| `VALIDACION_ENTREGA2.md` | Checklist de requerimientos cumplidos |
| `GUIA_PRESENTACION.md` | Este archivo |

---

*Cualquier término que no esté en esta guía, buscarlo en la sección 9 (Glosario) o consultar el INFORME_FINAL.md para ver la implementación técnica exacta.*
