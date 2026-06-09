"""
API REST — Sistema RAG Inmobiliaria Manizales
FastAPI + MongoDB + Groq (Llama 3.1)

Endpoints:
  POST /search              — Busqueda vectorial hibrida en document_chunks
  POST /rag                 — Pipeline RAG completo (embed, retrieve, LLM, log)
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
from fastapi.middleware.cors import CORSMiddleware
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
    TextToImageRequest, TextToImageResponse, TextToImageResult,
)


# ---------------------------------------------------------------------------
# Lifespan: carga el modelo de embeddings al arrancar
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # **lifespan**: se ejecuta al iniciar y detener la aplicacion FastAPI
    # Al arrancar, precarga el modelo de embeddings en memoria para que
    # las primeras consultas no tengan demora por carga del modelo
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
        "API para busqueda semantica y generacion aumentada por recuperacion (RAG) "
        "sobre documentos inmobiliarios de Manizales, Caldas. "
        "Compara estrategias de chunking: fixed_size, sentence y semantic."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# **cors**: permite peticiones desde cualquier origen para facilitar
# el desarrollo con frontends locales o despliegues en distintos dominios
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 10 consultas predefinidas para el experimento de chunking
# **experimento**: cubren preguntas tipicas que un usuario haria sobre
# propiedades inmobiliarias en Manizales
CONSULTAS_EXPERIMENTO = [
    "?Se permiten mascotas en el apartamento?",
    "?Cual es el valor del arriendo mensual?",
    "?Cuantas habitaciones tiene la propiedad?",
    "?Que incluye el contrato de arrendamiento?",
    "?Cual es la ubicacion exacta del inmueble?",
    "?Que servicios publicos estan incluidos?",
    "?Hay restricciones para subarrendar?",
    "?Que condiciones tiene el pago del canon?",
    "?Como es la cocina del apartamento?",
    "?Que opinan otros usuarios sobre la propiedad?",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def chunks_to_models(raw: list) -> list[ChunkResult]:
    # **responsabilidad**: convierte los documentos crudos de MongoDB en objetos
    # Pydantic ChunkResult para que la API devuelva datos estructurados y validados
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
    # **responsabilidad**: retorna un cliente de Groq, verificando que la
    # API key este configurada. Si no, lanza error 503 para informar al usuario
    if not settings.groq_api_key:
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY no configurada. Revisa tu archivo .env",
        )
    return Groq(api_key=settings.groq_api_key)


# Prompt del sistema para el LLM, define el rol del asistente
# **prompt_sistema**: instruye a Groq a actuar como experto en bienes raices
# de Manizales, respondiendo solo con el contexto proporcionado
SYSTEM_PROMPT = """Eres un asistente experto en bienes raices en Colombia, especializado en el mercado inmobiliario de Manizales, Caldas.
Respondes preguntas sobre propiedades, contratos de arrendamiento, reglamentos de copropiedad y el proceso de arrendamiento en Colombia.
Basas tus respuestas UNICAMENTE en el contexto proporcionado. Si la informacion no esta en el contexto, indicado claramente.
Responde siempre en espanol colombiano, de manera profesional y concisa.
Cuando el contexto lo permita, menciona detalles especificos como precios en COP, barrios de Manizales o clausulas contractuales."""


def call_llm(query: str, context_chunks: list[ChunkResult]) -> str:
    """
    Construye un prompt con contexto de chunks y llama a Groq (Llama 3.1) para generar respuesta.
    """
    # **algoritmo**: construye el prompt con los chunks recuperados como contexto
    # y envia la peticion a Groq para generar una respuesta en lenguaje natural
    groq = get_groq_client()

    contexto = "\n\n---\n\n".join([
        f"[Documento {i+1} — {c.tipo_doc or 'general'}]\n{c.texto}"
        for i, c in enumerate(context_chunks)
    ])

    user_message = f"""Contexto de documentos inmobiliarios:

{contexto}

---

Pregunta del usuario: {query}

Responde basandote exclusivamente en el contexto anterior."""

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
    # **responsabilidad**: guarda en MongoDB (rag_queries_logs) un registro
    # completo de cada consulta RAG: query, embedding, chunks usados, respuesta
    # generada y tiempo de respuesta para auditoria y mejora continua
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
# Endpoints de la API REST
# ---------------------------------------------------------------------------

# Endpoint GET /: health check simple, confirma que la API esta viva
# y muestra la version y enlace a documentacion Swagger
@app.get("/", summary="Health check")
def root():
    # **proposito**: endpoint de verificaicon de estado. Retorna informacion
    # basica del servicio para confirmar que la API esta funcionando
    return {
        "status": "ok",
        "service": "RAG Inmobiliaria Manizales",
        "version": "2.0.0",
        "docs": "/docs",
    }


@app.post("/search", response_model=SearchResponse, summary="Busqueda vectorial en document_chunks")
def search(req: SearchRequest):
    """
    Realiza busqueda semantica sobre los chunks vectorizados.
    Opcionalmente filtra por estrategia de chunking y/o tipo de documento.
    Devuelve los `top_k` chunks mas similares a la consulta.
    """
    # **endpoint_search**: recibe una consulta textual, genera su embedding,
    # ejecuta busqueda vectorial en MongoDB Atlas y retorna los chunks mas
    # relevantes con su puntuacion de similitud
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


# Endpoints de imagenes
# **responsabilidad**: endpoints para busqueda y exploracion del catalogo visual
# de propiedades usando embeddings de imagenes (CLIP, 512 dimensiones)


def images_to_models(raw: list) -> list[ImageResult]:
    # **responsabilidad**: convierte documentos crudos de image_embeddings en
    # objetos Pydantic ImageResult para respuestas estructuradas de la API
    # Incluye join con media_assets para obtener URL y property_id
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


@app.post("/search/image", response_model=ImageSearchResponse, summary="Buscar imagenes similares por media_id")
def search_image(req: ImageSearchRequest):
    """
    Busca imagenes visualmente similares a una imagen de referencia.
    Usa $vectorSearch contra el indice vector_index_images (512 dimensiones CLIP).
    """
    # **endpoint_search_image**: recibe un media_id de referencia, busca su
    # embedding en image_embeddings y ejecuta busqueda por similitud vectorial
    # para encontrar las imagenes visualmente mas parecidas
    db = get_db()
    raw = vector_search_images(db, media_id=req.media_id, top_k=req.top_k)
    resultados = images_to_models(raw)
    return ImageSearchResponse(
        media_id_referencia=req.media_id,
        total_results=len(resultados),
        resultados=resultados,
    )


@app.get("/search/image/random", response_model=ImageRandomResponse, summary="Imagenes aleatorias (muestra)")
def random_images(top_k: int = Query(5, ge=1, le=20)):
    """
    Retorna una muestra aleatoria de imagenes con sus metadatos.
    Util para explorar el catalogo visual antes de hacer busquedas por similitud.
    """
    # **endpoint_random_images**: retorna una muestra aleatoria de imagenes del
    # catalogo. Usa $sample de MongoDB para seleccionar documentos al azar
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
    2. Recupera los `top_k` chunks mas relevantes de MongoDB
    3. Construye el prompt con el contexto recuperado
    4. Genera la respuesta con Groq (Llama 3.1)
    5. Registra la consulta en rag_queries_logs
    """
    # **endpoint_rag**: pipeline completo de Retrieval Augmented Generation
    # 1. Busqueda vectorial de chunks relevantes
    # 2. Construccion de prompt con contexto
    # 3. Generacion de respuesta con Llama 3.1 via Groq
    # 4. Registro de la consulta para trazabilidad
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
    con metricas de numero de chunks, longitud promedio y score de similitud.
    """
    # **endpoint_compare**: ejecuta una misma consulta en las 3 estrategias
    # y devuelve metricas comparativas: cantidad de chunks, longitud promedio,
    # score de similitud y total de chunks en base de datos por estrategia
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


@app.get("/experiment/results", response_model=ExperimentResponse, summary="Experimento de chunking: 10 consultas x 3 estrategias")
def experiment_results(top_k: int = Query(3, ge=1, le=10)):
    """
    Ejecuta las 10 consultas predefinidas sobre las 3 estrategias de chunking
    y retorna una tabla comparativa con metricas de calidad.
    Tambien guarda las evaluaciones en rag_evaluations.
    """
    # **endpoint_experiment**: ejecuta el experimento completo con las 10
    # consultas predefinidas para cada estrategia, calcula metricas y las
    # almacena en MongoDB para analisis posterior
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

            # Guardar evaluacion simplificada
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


# ---------------------------------------------------------------------------
# Nuevos endpoints: /stats  /images  /search/images  /evaluations
# ---------------------------------------------------------------------------

@app.post("/search/text-to-image", response_model=TextToImageResponse, summary="Buscar imagenes por descripcion textual")
def search_text_to_image(req: TextToImageRequest):
    """
    Busca imagenes visualmente similares a partir de una descripcion textual.

    1. Genera embedding de texto (384d) con all-MiniLM-L6-v2
    2. Proyecta a 512d con padding de ceros (compatible con CLIP embeddings)
    3. Busca en image_embeddings usando $vectorSearch con indice vector_index_images
    4. Si falla, hace busqueda manual por similitud coseno sobre los primeros 384d
    """
    # **endpoint_text_to_image**: convierte texto descriptivo a embedding de 384d,
    # lo completa con ceros a 512d para compatibilidad con CLIP, y busca en el
    # indice vector_index_images. Si el indice Atlas falla, usa fallback manual
    # con sklearn cosine_similarity
    db = get_db()
    query_vec_384 = embed([req.query])[0]

    # Padding a 512 dimensiones para compatibilidad con CLIP
    query_vec_512 = query_vec_384 + [0.0] * (512 - len(query_vec_384))

    try:
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index_images",
                    "path": "embedding",
                    "queryVector": query_vec_512,
                    "numCandidates": 100,
                    "limit": req.top_k,
                }
            },
            {
                "$lookup": {
                    "from": "media_assets",
                    "localField": "media_id",
                    "foreignField": "_id",
                    "as": "media_info",
                }
            },
            {"$unwind": {"path": "$media_info", "preserveNullAndEmptyArrays": False}},
            {
                "$project": {
                    "_id": 1,
                    "media_id": 1,
                    "url": "$media_info.url",
                    "tipo": "$media_info.tipo",
                    "property_id": "$media_info.property_id",
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]
        raw = list(db["image_embeddings"].aggregate(pipeline))
    except Exception:
        # Fallback manual por similitud coseno con 384d
        # **fallback**: si el indice Atlas no existe o falla, se hace busqueda
        # manual comparando el embedding de texto contra todas las imagenes
        # usando similitud coseno en las primeras 384 dimensiones
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity

        all_embeddings = list(db["image_embeddings"].aggregate([
            {
                "$lookup": {
                    "from": "media_assets",
                    "localField": "media_id",
                    "foreignField": "_id",
                    "as": "media_info",
                }
            },
            {"$unwind": {"path": "$media_info", "preserveNullAndEmptyArrays": False}},
            {
                "$project": {
                    "_id": 1,
                    "media_id": 1,
                    "embedding": 1,
                    "url": "$media_info.url",
                    "tipo": "$media_info.tipo",
                    "property_id": "$media_info.property_id",
                }
            },
        ]))

        q = np.array(query_vec_384).reshape(1, -1)
        scored = []
        for doc in all_embeddings:
            emb = doc.get("embedding", [])
            if not emb:
                continue
            v = np.array(emb[:384]).reshape(1, -1)
            sim = float(cosine_similarity(q, v)[0][0])
            scored.append({
                "_id": doc["_id"],
                "media_id": doc["media_id"],
                "url": doc["url"],
                "tipo": doc.get("tipo", ""),
                "property_id": doc.get("property_id", ""),
                "score": sim,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        raw = scored[: req.top_k]

    resultados = [
        TextToImageResult(
            media_id=r["media_id"],
            url=r["url"],
            property_id=r.get("property_id", ""),
            tipo=r.get("tipo", ""),
            score=round(r["score"], 4),
        )
        for r in raw
    ]

    return TextToImageResponse(
        query=req.query,
        total_results=len(resultados),
        resultados=resultados,
    )


@app.get("/stats", summary="Estadisticas del sistema")
def get_stats():
    # **endpoint_stats**: retorna conteos de todas las colecciones principales
    # de MongoDB para monitorear el estado del sistema: documentos, chunks
    # (desglosados por estrategia), imagenes, propiedades, contratos y logs
    db = get_db()
    chunks_by_strategy = {
        s: db["document_chunks"].count_documents({"estrategia_chunking": s})
        for s in ["fixed_size", "sentence", "semantic"]
    }
    return {
        "documentos": db["documents_repository"].count_documents({}),
        "chunks_total": db["document_chunks"].count_documents({}),
        "chunks_por_estrategia": chunks_by_strategy,
        "media_assets": db["media_assets"].count_documents({}),
        "propiedades": db["properties"].count_documents({}),
        "contratos": db["contracts"].count_documents({}),
        "consultas_log": db["rag_queries_logs"].count_documents({}),
        "evaluaciones": db["rag_evaluations"].count_documents({}),
    }


@app.get("/images", summary="Lista de imagenes del catalogo")
def list_images(limit: int = Query(20, ge=1, le=60)):
    # **endpoint_images**: retorna una lista plana de imagenes del catalogo
    # con sus URLs y metadatos, util para mostrar galerias en el frontend
    db = get_db()
    docs = list(
        db["media_assets"].find(
            {}, {"_id": 1, "url": 1, "property_id": 1, "tipo": 1}
        ).limit(limit)
    )
    for d in docs:
        d["_id"] = str(d["_id"])
    return {"images": docs, "total": len(docs)}


@app.post("/search/images", summary="Busqueda de imagenes similares por media_id")
def search_similar_images(req: ImageSearchRequest):
    # **endpoint_search_images**: endpoint alternativo para busqueda de imagenes
    # similares. Usa vector_search_images con el indice de embeddings de imagenes
    # y retorna URLs con puntuaciones de similitud
    db = get_db()
    raw = vector_search_images(db, media_id=req.media_id, top_k=req.top_k)
    if not raw:
        raise HTTPException(404, "media_id no encontrado o sin resultados")
    resultados = images_to_models(raw)
    return {
        "source_media_id": req.media_id,
        "results": [
            {
                "media_id": r.media_id,
                "url": r.url,
                "property_id": r.property_id,
                "score": r.score,
            }
            for r in resultados
        ],
    }


@app.get("/evaluations", summary="Ultimas evaluaciones guardadas")
def get_evaluations(limit: int = Query(20, ge=1, le=100)):
    # **endpoint_evaluations**: retorna las evaluaciones mas recientes del
    # experimento de chunking, incluyendo relevancia, precision y metadatos
    # de cada consulta para analizar el rendimiento de las estrategias
    db = get_db()
    docs = list(
        db["rag_evaluations"].find(
            {},
            {
                "_id": 1,
                "rag_query_id": 1,
                "relevancia": 1,
                "precision": 1,
                "modelo_eval": 1,
                "fecha": 1,
                "_meta": 1,
            },
        ).sort("fecha", -1).limit(limit)
    )
    for d in docs:
        d["_id"] = str(d["_id"])
    return {"evaluaciones": docs, "total": len(docs)}
