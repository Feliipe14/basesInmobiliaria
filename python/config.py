"""Configuración centralizada desde variables de entorno."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://127.0.0.1:27017"
    db_name: str = "Inmobiliaria_RAG_NoSQL"
    groq_api_key: str = ""

    # Parámetros de embeddings
    text_embedding_model: str = "all-MiniLM-L6-v2"
    text_embedding_dim: int = 384
    image_embedding_dim: int = 512

    # Parámetros de chunking
    fixed_chunk_size: int = 1024       # ~256 tokens × 4 chars/token
    fixed_chunk_overlap: int = 128     # ~32 tokens
    sentence_max_sentences: int = 5
    sentence_overlap: int = 1
    semantic_threshold: float = 0.80

    # RAG
    top_k_chunks: int = 5
    groq_model: str = "llama-3.1-8b-instant"

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
