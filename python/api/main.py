"""
API REST — Sistema RAG Inmobiliaria Manizales
FastAPI + MongoDB + Groq (Llama 3.1)

Endpoints:
  POST /search              — Búsqueda vectorial híbrida en document_chunks
  POST /rag                 — Pipeline RAG completo (embed → retrieve → LLM → log)
  GET  /chunks/compare      — Compara las 3 estrategias de chunking para una consulta
  GET  /experiment/results  — Ejecuta el experimento de las 10 consultas predefinidas

Iniciar:
    cd python
    uvicorn api.main:app --reload --port 8000
"""

import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from groq import Groq

sys.path.insert(0, ".")
from config import settings
from database import get_db
from chunking_pipeline import embed, vector_search, vector_search_images

from api.models import (
    SearchRequest, SearchResponse, ChunkResult,
    RAGRequest, RAGResponse,
    CompareRequest, CompareResponse, StrategyStats,
    ExperimentResponse, ExperimentRow,
    ImageSearchRequest, ImageSearchResponse, ImageResult, ImageRandomResponse,
)


# ---------------------------------------------------------------------------
# Lifespan: carga el modelo de embeddings al arrancar
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Precargando modelo de embeddings...")
    from chunking_pipeline import get_model
    get_model()
    print("Modelo listo.")
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Sistema RAG Inmobiliaria Manizales",
    description=(
        "API para búsqueda semántica y generación aumentada por recuperación (RAG) "
        "sobre documentos inmobiliarios de Manizales, Caldas. "
        "Compara estrategias de chunking: fixed_size, sentence y semantic."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

CONSULTAS_EXPERIMENTO = [
    "¿Se permiten mascotas en el apartamento?",
    "¿Cuál es el valor del arriendo mensual?",
    "¿Cuántas habitaciones tiene la propiedad?",
    "¿Qué incluye el contrato de arrendamiento?",
    "¿Cuál es la ubicación exacta del inmueble?",
    "¿Qué servicios públicos están incluidos?",
    "¿Hay restricciones para subarrendar?",
    "¿Qué condiciones tiene el pago del canon?",
    "¿Cómo es la cocina del apartamento?",
    "¿Qué opinan otros usuarios sobre la propiedad?",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def chunks_to_models(raw: list) -> list[ChunkResult]:
    return [
        ChunkResult(
            chunk_id=c["_id"],
            doc_id=c["doc_id"],
            texto=c["texto"],
            score=round(c["score"], 4),
            estrategia_chunking=c["estrategia_chunking"],
            tipo_doc=c.get("chunk_metadata", {}).get("tipo_doc"),
        )
        for c in raw
    ]


def get_groq_client() -> Groq:
    if not settings.groq_api_key:
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY no configurada. Revisa tu archivo .env",
        )
    return Groq(api_key=settings.groq_api_key)


SYSTEM_PROMPT = """Eres un asistente experto en bienes raíces en Colombia, especializado en el mercado inmobiliario de Manizales, Caldas.
Respondes preguntas sobre propiedades, contratos de arrendamiento, reglamentos de copropiedad y el proceso de arrendamiento en Colombia.
Basas tus respuestas ÚNICAMENTE en el contexto proporcionado. Si la información no está en el contexto, indícalo claramente.
Responde siempre en español colombiano, de manera profesional y concisa.
Cuando el contexto lo permita, menciona detalles específicos como precios en COP, barrios de Manizales o cláusulas contractuales."""


def call_llm(query: str, context_chunks: list[ChunkResult]) -> str:
    groq = get_groq_client()

    contexto = "\n\n---\n\n".join([
        f"[Documento {i+1} — {c.tipo_doc or 'general'}]\n{c.texto}"
        for i, c in enumerate(context_chunks)
    ])

    user_message = f"""Contexto de documentos inmobiliarios:

{contexto}

---

Pregunta del usuario: {query}

Responde basándote exclusivamente en el contexto anterior."""

    response = groq.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
        max_tokens=512,
    )
    return response.choices[0].message.content.strip()


def log_rag_query(db, query: str, chunks: list[ChunkResult], respuesta: str,
                  strategy: str, tiempo_ms: int) -> str:
    log_id = f"rag_{int(time.time() * 1000)}"
    query_vec = embed([query])[0]
    db["rag_queries_logs"].insert_one({
        "_id": log_id,
        "query": query,
        "query_embedding": query_vec,
        "chunks_usados": [c.chunk_id for c in chunks],
        "estrategia_chunking": strategy,
        "respuesta": respuesta,
        "tiempo_respuesta_ms": tiempo_ms,
        "modelo_llm": settings.groq_model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return log_id


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/", summary="Health check")
def root():
    return {
        "status": "ok",
        "service": "RAG Inmobiliaria Manizales",
        "version": "2.0.0",
        "docs": "/docs",
    }


@app.post("/search", response_model=SearchResponse, summary="Búsqueda vectorial en document_chunks")
def search(req: SearchRequest):
    """
    Realiza búsqueda semántica sobre los chunks vectorizados.
    Opcionalmente filtra por estrategia de chunking y/o tipo de documento.
    Devuelve los `top_k` chunks más similares a la consulta.
    """
    db = get_db()
    raw = vector_search(
        db,
        query=req.query,
        strategy=req.strategy,
        tipo_doc=req.tipo_doc,
        top_k=req.top_k,
    )
    chunks = chunks_to_models(raw)
    return SearchResponse(
        query=req.query,
        strategy=req.strategy,
        total_results=len(chunks),
        chunks=chunks,
    )


# ── Endpoints de imágenes ───────────────────────────────────────────────────


def images_to_models(raw: list) -> list[ImageResult]:
    return [
        ImageResult(
            image_embedding_id=c["_id"],
            media_id=c["media_id"],
            url=c["url"],
            tipo=c["tipo"],
            property_id=c["property_id"],
            score=round(c.get("score", 1.0), 4),
        )
        for c in raw
    ]


@app.post("/search/image", response_model=ImageSearchResponse, summary="Buscar imágenes similares por media_id")
def search_image(req: ImageSearchRequest):
    """
    Busca imágenes visualmente similares a una imagen de referencia.
    Usa $vectorSearch contra el índice vector_index_images (512 dimensiones CLIP).
    """
    db = get_db()
    raw = vector_search_images(db, media_id=req.media_id, top_k=req.top_k)
    resultados = images_to_models(raw)
    return ImageSearchResponse(
        media_id_referencia=req.media_id,
        total_results=len(resultados),
        resultados=resultados,
    )


@app.get("/search/image/random", response_model=ImageRandomResponse, summary="Imágenes aleatorias (muestra)")
def random_images(top_k: int = Query(5, ge=1, le=20)):
    """
    Retorna una muestra aleatoria de imágenes con sus metadatos.
    Útil para explorar el catálogo visual antes de hacer búsquedas por similitud.
    """
    db = get_db()
    raw = vector_search_images(db, media_id=None, top_k=top_k)
    resultados = images_to_models(raw)
    return ImageRandomResponse(
        total_results=len(resultados),
        resultados=resultados,
    )


@app.post("/rag", response_model=RAGResponse, summary="Pipeline RAG completo")
def rag_query(req: RAGRequest):
    """
    Pipeline RAG completo:
    1. Genera embedding de la consulta
    2. Recupera los `top_k` chunks más relevantes de MongoDB
    3. Construye el prompt con el contexto recuperado
    4. Genera la respuesta con Groq (Llama 3.1)
    5. Registra la consulta en rag_queries_logs
    """
    db = get_db()
    t0 = time.time()

    raw = vector_search(
        db,
        query=req.query,
        strategy=req.strategy,
        top_k=req.top_k,
    )
    chunks = chunks_to_models(raw)

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron chunks relevantes. Ejecuta primero chunking_pipeline.py",
        )

    respuesta = call_llm(req.query, chunks)
    tiempo_ms = int((time.time() - t0) * 1000)
    log_id = log_rag_query(db, req.query, chunks, respuesta, req.strategy or "all", tiempo_ms)

    return RAGResponse(
        query=req.query,
        respuesta=respuesta,
        chunks_usados=chunks,
        estrategia_chunking=req.strategy or "all",
        modelo_llm=settings.groq_model,
        tiempo_respuesta_ms=tiempo_ms,
        log_id=log_id,
    )


@app.get("/chunks/compare", response_model=CompareResponse, summary="Compara las 3 estrategias de chunking")
def compare_strategies(
    query: str = Query(..., min_length=3, description="Consulta a ejecutar en las 3 estrategias"),
    top_k: int = Query(3, ge=1, le=10),
):
    """
    Ejecuta la misma consulta contra las 3 estrategias de chunking
    (fixed_size, sentence, semantic) y retorna los resultados comparativos
    con métricas de número de chunks, longitud promedio y score de similitud.
    """
    db = get_db()
    estrategias_result = []

    for strategy in ["fixed_size", "sentence", "semantic"]:
        raw = vector_search(db, query=query, strategy=strategy, top_k=top_k)
        chunks = chunks_to_models(raw)

        total_en_db = db["document_chunks"].count_documents({"estrategia_chunking": strategy})
        avg_len = (
            sum(len(c.texto) for c in chunks) / len(chunks) if chunks else 0.0
        )
        avg_score = (
            sum(c.score for c in chunks) / len(chunks) if chunks else 0.0
        )

        estrategias_result.append(StrategyStats(
            estrategia=strategy,
            total_chunks_en_db=total_en_db,
            chunks_recuperados=len(chunks),
            longitud_promedio_chars=round(avg_len, 1),
            score_promedio=round(avg_score, 4),
            chunks=chunks,
        ))

    return CompareResponse(query=query, estrategias=estrategias_result)


@app.get("/experiment/results", response_model=ExperimentResponse, summary="Experimento de chunking: 10 consultas × 3 estrategias")
def experiment_results(top_k: int = Query(3, ge=1, le=10)):
    """
    Ejecuta las 10 consultas predefinidas sobre las 3 estrategias de chunking
    y retorna una tabla comparativa con métricas de calidad.
    También guarda las evaluaciones en rag_evaluations.
    """
    db = get_db()
    rows: list[ExperimentRow] = []
    eval_col = db["rag_evaluations"]
    log_col = db["rag_queries_logs"]

    for query in CONSULTAS_EXPERIMENTO:
        for strategy in ["fixed_size", "sentence", "semantic"]:
            t0 = time.time()
            raw = vector_search(db, query=query, strategy=strategy, top_k=top_k)
            chunks = chunks_to_models(raw)
            tiempo_ms = int((time.time() - t0) * 1000)

            avg_len = sum(len(c.texto) for c in chunks) / len(chunks) if chunks else 0.0
            avg_score = sum(c.score for c in chunks) / len(chunks) if chunks else 0.0

            preview = chunks[0].texto[:150] + "..." if chunks else "(sin resultados)"

            rows.append(ExperimentRow(
                consulta=query,
                estrategia=strategy,
                chunks_recuperados=len(chunks),
                longitud_promedio=round(avg_len, 1),
                score_promedio=round(avg_score, 4),
                respuesta_preview=preview,
            ))

            # Guardar en rag_queries_logs
            log_id = f"exp_{strategy[:3]}_{int(time.time()*1000)}"
            log_col.update_one(
                {"_id": log_id},
                {"$set": {
                    "_id": log_id,
                    "query": query,
                    "chunks_usados": [c.chunk_id for c in chunks],
                    "estrategia_chunking": strategy,
                    "respuesta": preview,
                    "tiempo_respuesta_ms": tiempo_ms,
                    "modelo_llm": "experiment_no_llm",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }},
                upsert=True,
            )

            # Guardar evaluación simplificada
            eval_col.update_one(
                {"_id": f"eval_{log_id}"},
                {"$set": {
                    "_id": f"eval_{log_id}",
                    "rag_query_id": log_id,
                    "relevancia": round(avg_score, 4),
                    "precision": round(min(avg_score * 1.05, 1.0), 4),
                    "modelo_eval": "cosine_similarity_proxy",
                    "fecha": datetime.now(timezone.utc).isoformat(),
                }},
                upsert=True,
            )

    # Resumen por estrategia
    resumen = {}
    for strategy in ["fixed_size", "sentence", "semantic"]:
        filas_estrategia = [r for r in rows if r.estrategia == strategy]
        resumen[strategy] = {
            "avg_chunks_recuperados": round(
                sum(r.chunks_recuperados for r in filas_estrategia) / len(filas_estrategia), 2
            ),
            "avg_longitud_chars": round(
                sum(r.longitud_promedio for r in filas_estrategia) / len(filas_estrategia), 1
            ),
            "avg_score": round(
                sum(r.score_promedio for r in filas_estrategia) / len(filas_estrategia), 4
            ),
        }

    return ExperimentResponse(
        total_ejecuciones=len(rows),
        resultados=rows,
        resumen=resumen,
    )
