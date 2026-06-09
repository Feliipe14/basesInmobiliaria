# Sistema RAG NoSQL — Inmobiliaria Manizales

**Bases de Datos No Relacionales — Segunda Entrega**  
Universidad | Junio 2025

Sistema de Recuperación Aumentada por Generación (RAG) aplicado al dominio inmobiliario de Manizales, Caldas, Colombia. Compara tres estrategias de chunking sobre una colección de 100+ documentos almacenados en MongoDB Atlas.

---

## Arquitectura

```
┌─────────────────────────────────────────────────────┐
│                   FastAPI (puerto 8000)              │
│  POST /search  POST /rag  GET /chunks/compare       │
│  GET /experiment/results  GET /docs (Swagger)        │
└──────────────────────┬──────────────────────────────┘
                       │
         ┌─────────────▼──────────────┐
         │   Pipeline de Chunks       │
         │  fixed_size │ sentence │  │
         │  semantic                  │
         │  SentenceTransformer       │
         │  all-MiniLM-L6-v2 (384d)  │
         └─────────────┬──────────────┘
                       │
         ┌─────────────▼──────────────┐
         │   MongoDB Atlas            │
         │  14 colecciones            │
         │  document_chunks (RAG)     │
         │  rag_queries_logs          │
         └─────────────┬──────────────┘
                       │
         ┌─────────────▼──────────────┐
         │   Groq API                 │
         │  llama-3.1-8b-instant     │
         └────────────────────────────┘
```

---

## Colecciones MongoDB (14)

| Colección | Descripción |
|---|---|
| `users` | Propietarios, arrendatarios y agentes |
| `agencies` | Agencias inmobiliarias |
| `properties` | Inmuebles con coordenadas GeoJSON |
| `listings` | Publicaciones comerciales |
| `contracts` | Contratos de arrendamiento |
| `chat_sessions` | Conversaciones entre partes |
| `media_assets` | Imágenes y multimedia |
| `maintenance_requests` | Solicitudes de mantenimiento |
| `reviews` | Reseñas de propiedades |
| `documents_repository` | Documentos crudos para RAG |
| `document_chunks` | Chunks vectorizados (núcleo RAG) |
| `image_embeddings` | Vectores CLIP de imágenes |
| `rag_queries_logs` | Historial de consultas |
| `rag_evaluations` | Métricas de calidad RAG |

---

## Requisitos previos

- Node.js 18+ (para `init-db.js`)
- Python 3.11+
- Cuenta gratuita en [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
- Cuenta gratuita en [Groq Console](https://console.groq.com)

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone <url-del-repo>
cd basesInmobiliaria
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tu MONGODB_URI y GROQ_API_KEY
```

### 3. Instalar dependencias Node.js

```bash
npm install
```

### 4. Instalar dependencias Python

```bash
cd python
pip install -r requirements.txt
# Descargar datos de NLTK (para tokenización de oraciones)
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"
```

---

## Ejecución paso a paso

### Paso 1 — Inicializar la base de datos (Node.js)

```bash
# Desde la raíz del proyecto
npm run db:init
```

Crea las 14 colecciones con validadores JSON Schema e índices.

### Paso 2 — Cargar el dataset de prueba (Python)

```bash
cd python
python generate_dataset.py
```

Genera y carga en MongoDB:
- 13 usuarios, 3 agencias, 20 propiedades
- 20 listings, 15 contratos
- 60 media_assets, 15 reseñas
- **100 documentos** en `documents_repository`
- 60 image_embeddings simulados (CLIP 512-dim)

### Paso 3 — Ejecutar el pipeline de chunking

```bash
python chunking_pipeline.py
# O solo una estrategia:
python chunking_pipeline.py --strategy semantic
```

Aplica las 3 estrategias a los 100 documentos y guarda los chunks vectorizados en `document_chunks`. El modelo `all-MiniLM-L6-v2` se descarga automáticamente (~90 MB).

**Estrategias implementadas:**
| Estrategia | Configuración | Descripción |
|---|---|---|
| `fixed_size` | chunk_size=1024 chars (~256 tokens), overlap=128 | Tamaño fijo, simple y rápido |
| `sentence` | max=5 oraciones, overlap=1 | Respeta límites de oraciones |
| `semantic` | threshold=0.80 coseno | Detecta cambios de tema |

### Paso 4 — Configurar Vector Search Index en Atlas

> **Nota**: Solo requerido si tienes clúster M10 o superior.  
> En M0 (gratuito), la API usa búsqueda vectorial manual (coseno en Python).

En Atlas UI → tu clúster → **Search** → **Create Search Index** → **JSON Editor**:

**Para `document_chunks` (384 dimensiones):**
```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 384,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "estrategia_chunking"
    }
  ]
}
```
Nombre del índice: `vector_index_chunks`

**Para `image_embeddings` (512 dimensiones):**
```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 512,
      "similarity": "cosine"
    }
  ]
}
```
Nombre del índice: `vector_index_images`

### Paso 5 — Iniciar la API

```bash
cd python
uvicorn api.main:app --reload --port 8000
```

Abre en el navegador: **http://localhost:8000/docs** (Swagger UI automático)

### Paso 6 — Ejecutar el experimento de chunking

```bash
cd python
python experiment.py
```

Ejecuta las 10 consultas predefinidas sobre las 3 estrategias y muestra una tabla comparativa en consola.

---

## Endpoints de la API

### `POST /search` — Búsqueda vectorial

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "¿Se permiten mascotas en el apartamento?",
    "strategy": "semantic",
    "top_k": 5
  }'
```

### `POST /rag` — Respuesta generada por LLM

```bash
curl -X POST http://localhost:8000/rag \
  -H "Content-Type: application/json" \
  -d '{
    "query": "¿Cuál es el valor del arriendo mensual?",
    "strategy": "semantic",
    "top_k": 3
  }'
```

### `GET /chunks/compare` — Comparación de estrategias

```bash
curl "http://localhost:8000/chunks/compare?query=¿Cuántas+habitaciones+tiene?&top_k=3"
```

### `GET /experiment/results` — Tabla del experimento completo

```bash
curl "http://localhost:8000/experiment/results?top_k=3"
```

---

## Dataset generado

| Tipo de documento | Cantidad | Longitud promedio |
|---|---|---|
| Descripciones de propiedades | 20 | ~600 palabras |
| Contratos de arrendamiento | 15 | ~800 palabras |
| Reglamentos de copropiedad | 15 | ~700 palabras |
| Transcripciones de chat | 15 | ~400 palabras |
| Reportes de mercado | 10 | ~500 palabras |
| FAQs y políticas | 5 | ~400 palabras |
| Guías de mantenimiento | 2 | ~450 palabras |
| **Total** | **82+** | — |

> Los 100+ documentos provienen de combinar los anteriores con variaciones por barrio y tipo de inmueble.

---

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Base de datos | MongoDB Atlas (NoSQL documental) |
| Embeddings de texto | `sentence-transformers` — `all-MiniLM-L6-v2` (384 dims) |
| Embeddings de imagen | CLIP simulado (512 dims) |
| Chunking fixed-size | `langchain-text-splitters` — `RecursiveCharacterTextSplitter` |
| Chunking sentence | Implementación propia con regex español |
| Chunking semantic | Implementación propia con `scikit-learn` cosine_similarity |
| API REST | `FastAPI` + `uvicorn` |
| LLM | Groq API — `llama-3.1-8b-instant` |
| Driver MongoDB | `pymongo` |

---

## Estructura del repositorio

```
basesInmobiliaria/
├── scripts/
│   ├── init-db.js          # Inicialización idempotente de MongoDB (Node.js)
│   └── seed-data.js        # Seed básico legacy
├── python/
│   ├── requirements.txt    # Dependencias Python
│   ├── config.py           # Configuración desde .env
│   ├── database.py         # Conexión MongoDB singleton
│   ├── generate_dataset.py # Genera 100+ documentos y carga el dataset
│   ├── chunking_pipeline.py # Pipeline de chunking + embeddings (3 estrategias)
│   ├── experiment.py       # Experimento comparativo (10 consultas × 3 estrategias)
│   └── api/
│       ├── main.py         # FastAPI — todos los endpoints
│       └── models.py       # Modelos Pydantic request/response
├── .env                    # Variables de entorno (NO subir a Git)
├── .env.example            # Plantilla de variables de entorno
├── .gitignore
├── package.json
└── README.md
```
