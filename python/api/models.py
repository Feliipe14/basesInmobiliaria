"""Modelos Pydantic para request/response de la API RAG Inmobiliaria."""

from typing import List, Optional
from pydantic import BaseModel, Field


# Requests
# **responsabilidad**: definir la estructura y validacion de los datos que
# el cliente envia a cada endpoint de la API

class SearchRequest(BaseModel):
    # **proposito**: modelo para la busqueda vectorial de chunks
    # Recibe texto de consulta, estrategia de chunking opcional y cantidad de resultados
    query: str = Field(..., min_length=3, description="Texto de la consulta en espanol")
    strategy: Optional[str] = Field(
        None,
        pattern="^(fixed_size|sentence|semantic)$",
        description="Estrategia de chunking a consultar. Omitir para buscar en todas.",
    )
    tipo_doc: Optional[str] = Field(
        None,
        description="Filtrar por tipo de documento (descripcion_propiedad, contrato, etc.)",
    )
    top_k: int = Field(5, ge=1, le=20, description="Numero de chunks a retornar")


class RAGRequest(BaseModel):
    # **proposito**: modelo para el pipeline RAG completo
    # Incluye la pregunta, estrategia de chunking y cuantos chunks usar como contexto
    query: str = Field(..., min_length=3, description="Pregunta del usuario en espanol")
    strategy: Optional[str] = Field(
        "semantic",
        pattern="^(fixed_size|sentence|semantic)$",
        description="Estrategia de chunking a usar para recuperar contexto",
    )
    top_k: int = Field(5, ge=1, le=10, description="Chunks de contexto a recuperar")


class CompareRequest(BaseModel):
    # **proposito**: modelo para comparar las 3 estrategias con una misma consulta
    query: str = Field(..., min_length=3, description="Consulta a ejecutar en las 3 estrategias")
    top_k: int = Field(3, ge=1, le=10)


# Response components
# **responsabilidad**: definir la estructura de los datos que la API devuelve al cliente

class ChunkResult(BaseModel):
    # **proposito**: representa un fragmento de documento recuperado por busqueda vectorial
    # Incluye el texto, puntuacion de similitud y metadatos de la estrategia usada
    chunk_id: str
    doc_id: str
    texto: str
    score: float
    estrategia_chunking: str
    tipo_doc: Optional[str] = None


class SearchResponse(BaseModel):
    # **proposito**: respuesta del endpoint /search con los chunks encontrados
    query: str
    strategy: Optional[str]
    total_results: int
    chunks: List[ChunkResult]


class RAGResponse(BaseModel):
    # **proposito**: respuesta del pipeline RAG con la respuesta generada por Groq
    # Incluye los chunks usados como contexto, el modelo LLM y tiempo de respuesta
    query: str
    respuesta: str
    chunks_usados: List[ChunkResult]
    estrategia_chunking: str
    modelo_llm: str
    tiempo_respuesta_ms: int
    log_id: str


class StrategyStats(BaseModel):
    # **proposito**: metricas de una estrategia para la comparativa de chunking
    estrategia: str
    total_chunks_en_db: int
    chunks_recuperados: int
    longitud_promedio_chars: float
    score_promedio: float
    chunks: List[ChunkResult]


class CompareResponse(BaseModel):
    # **proposito**: respuesta de la comparativa con las 3 estrategias de chunking
    query: str
    estrategias: List[StrategyStats]


class ExperimentRow(BaseModel):
    # **proposito**: una fila del experimento con los resultados de una consulta
    # en una estrategia especifica
    consulta: str
    estrategia: str
    chunks_recuperados: int
    longitud_promedio: float
    score_promedio: float
    respuesta_preview: str


class ExperimentResponse(BaseModel):
    # **proposito**: respuesta completa del experimento con todas las consultas
    # y un resumen por estrategia
    total_ejecuciones: int
    resultados: List[ExperimentRow]
    resumen: dict


# Imagenes
# **responsabilidad**: modelos para la busqueda y recuperacion de imagenes

class ImageSearchRequest(BaseModel):
    # **proposito**: solicitud para buscar imagenes similares a una imagen de referencia
    media_id: str = Field(
        ...,
        min_length=1,
        description="ID del media_asset de referencia para buscar imagenes similares",
    )
    top_k: int = Field(5, ge=1, le=20, description="Numero de imagenes similares a retornar")


class ImageResult(BaseModel):
    # **proposito**: resultado individual de busqueda de imagenes con su URL y metadatos
    image_embedding_id: str
    media_id: str
    url: str
    tipo: str
    property_id: str
    score: float


class ImageSearchResponse(BaseModel):
    # **proposito**: respuesta de busqueda de imagenes similares
    media_id_referencia: str
    total_results: int
    resultados: List[ImageResult]


class ImageRandomResponse(BaseModel):
    # **proposito**: respuesta con imagenes aleatorias del catalogo
    total_results: int
    resultados: List[ImageResult]


# Texto a Imagen
# **responsabilidad**: modelos para buscar imagenes a partir de descripcion textual

class TextToImageRequest(BaseModel):
    # **proposito**: solicitud para buscar imagenes por descripcion textual
    query: str = Field(..., min_length=3, description="Descripcion textual de la propiedad a buscar")
    top_k: int = Field(5, ge=1, le=20, description="Numero de imagenes a retornar")


class TextToImageResult(BaseModel):
    # **proposito**: resultado de busqueda texto-a-imagen con URL y puntuacion
    media_id: str
    url: str
    property_id: str
    tipo: str
    score: float


class TextToImageResponse(BaseModel):
    # **proposito**: respuesta de busqueda texto-a-imagen con la consulta original
    query: str
    total_results: int
    resultados: List[TextToImageResult]
