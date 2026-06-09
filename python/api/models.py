"""Modelos Pydantic para request/response de la API RAG Inmobiliaria."""

from typing import List, Optional
from pydantic import BaseModel, Field


# ── Requests ────────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Texto de la consulta en español")
    strategy: Optional[str] = Field(
        None,
        pattern="^(fixed_size|sentence|semantic)$",
        description="Estrategia de chunking a consultar. Omitir para buscar en todas.",
    )
    tipo_doc: Optional[str] = Field(
        None,
        description="Filtrar por tipo de documento (descripcion_propiedad, contrato, etc.)",
    )
    top_k: int = Field(5, ge=1, le=20, description="Número de chunks a retornar")


class RAGRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Pregunta del usuario en español")
    strategy: Optional[str] = Field(
        "semantic",
        pattern="^(fixed_size|sentence|semantic)$",
        description="Estrategia de chunking a usar para recuperar contexto",
    )
    top_k: int = Field(5, ge=1, le=10, description="Chunks de contexto a recuperar")


class CompareRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Consulta a ejecutar en las 3 estrategias")
    top_k: int = Field(3, ge=1, le=10)


# ── Response components ──────────────────────────────────────────────────────

class ChunkResult(BaseModel):
    chunk_id: str
    doc_id: str
    texto: str
    score: float
    estrategia_chunking: str
    tipo_doc: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    strategy: Optional[str]
    total_results: int
    chunks: List[ChunkResult]


class RAGResponse(BaseModel):
    query: str
    respuesta: str
    chunks_usados: List[ChunkResult]
    estrategia_chunking: str
    modelo_llm: str
    tiempo_respuesta_ms: int
    log_id: str


class StrategyStats(BaseModel):
    estrategia: str
    total_chunks_en_db: int
    chunks_recuperados: int
    longitud_promedio_chars: float
    score_promedio: float
    chunks: List[ChunkResult]


class CompareResponse(BaseModel):
    query: str
    estrategias: List[StrategyStats]


class ExperimentRow(BaseModel):
    consulta: str
    estrategia: str
    chunks_recuperados: int
    longitud_promedio: float
    score_promedio: float
    respuesta_preview: str


class ExperimentResponse(BaseModel):
    total_ejecuciones: int
    resultados: List[ExperimentRow]
    resumen: dict


# ── Imágenes ────────────────────────────────────────────────────────────────

class ImageSearchRequest(BaseModel):
    media_id: str = Field(
        ...,
        min_length=1,
        description="ID del media_asset de referencia para buscar imágenes similares",
    )
    top_k: int = Field(5, ge=1, le=20, description="Número de imágenes similares a retornar")


class ImageResult(BaseModel):
    image_embedding_id: str
    media_id: str
    url: str
    tipo: str
    property_id: str
    score: float


class ImageSearchResponse(BaseModel):
    media_id_referencia: str
    total_results: int
    resultados: List[ImageResult]


class ImageRandomResponse(BaseModel):
    total_results: int
    resultados: List[ImageResult]
