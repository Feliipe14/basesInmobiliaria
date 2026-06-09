"""Configuración centralizada desde variables de entorno."""

from pydantic_settings import BaseSettings


# Clase que centraliza toda la configuracion del sistema RAG
# **proposito**: cargar parametros desde variables de entorno o usar valores por defecto
class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://127.0.0.1:27017"
    db_name: str = "Inmobiliaria_RAG_NoSQL"
    groq_api_key: str = ""

    # Parametros de embeddings
    # **modelo**: all-MiniLM-L6-v2 genera vectores de 384 dimensiones para texto
    # Las imagenes usan CLIP con 512 dimensiones
    text_embedding_model: str = "all-MiniLM-L6-v2"
    text_embedding_dim: int = 384
    image_embedding_dim: int = 512

    # Parametros de chunking
    # **tamano_fijo**: 1024 caracteres por chunk equivalen a ~256 tokens
    # **superposicion**: 128 caracteres de overlap para no perder contexto entre chunks
    fixed_chunk_size: int = 1024
    fixed_chunk_overlap: int = 128
    sentence_max_sentences: int = 5
    sentence_overlap: int = 1
    semantic_threshold: float = 0.80

    # RAG
    # **top_k**: cuantos chunks recuperar como contexto para el LLM
    # **groq_model**: modelo Llama 3.1 8B para generar respuestas
    top_k_chunks: int = 5
    groq_model: str = "llama-3.1-8b-instant"

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Instancia global de configuracion lista para importar en cualquier modulo
# **singleton**: se crea una unica vez al importar este archivo
settings = Settings()
