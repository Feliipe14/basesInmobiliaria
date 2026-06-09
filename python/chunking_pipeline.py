"""
Pipeline de chunking y embeddings para el sistema RAG Inmobiliaria.

Aplica 3 estrategias de chunking a cada documento en documents_repository
y guarda los chunks vectorizados en document_chunks.

Estrategias implementadas:
  1. fixed_size   — RecursiveCharacterTextSplitter (chunk_size≈256 tokens)
  2. sentence     — Máximo 5 oraciones por chunk, overlap de 1 oración
  3. semantic     — Umbral de similitud coseno 0.80 entre oraciones adyacentes

Ejecutar:
    cd python
    python chunking_pipeline.py [--strategy all|fixed_size|sentence|semantic]
"""

import sys
import re
import argparse
from datetime import datetime, timezone
from typing import List

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from langchain_text_splitters import RecursiveCharacterTextSplitter

sys.path.insert(0, ".")
from config import settings
from database import get_db, close


# ---------------------------------------------------------------------------
# Modelo de embeddings (singleton)
# ---------------------------------------------------------------------------

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"  Cargando modelo {settings.text_embedding_model}...")
        _model = SentenceTransformer(settings.text_embedding_model)
    return _model


def embed(texts: List[str]) -> List[List[float]]:
    model = get_model()
    vecs = model.encode(texts, batch_size=32, show_progress_bar=False, normalize_embeddings=True)
    return vecs.tolist()


# ---------------------------------------------------------------------------
# Tokenización por oraciones (sin dependencia de NLTK)
# ---------------------------------------------------------------------------

def split_sentences(text: str) -> List[str]:
    """Divide texto en oraciones usando regex. Funciona bien para español."""
    text = text.strip()
    # Divide en puntos, signos de exclamación e interrogación seguidos de mayúscula o fin
    parts = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑÜ])", text)
    # Filtra oraciones muy cortas (ruido)
    return [p.strip() for p in parts if len(p.strip()) > 15]


# ---------------------------------------------------------------------------
# Estrategia 1: Fixed-size
# ---------------------------------------------------------------------------

def chunk_fixed_size(text: str) -> List[str]:
    """
    Divide el texto en chunks de tamaño fijo.
    chunk_size=1024 chars ≈ 256 tokens (ratio ~4 chars/token).
    chunk_overlap=128 chars ≈ 32 tokens.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.fixed_chunk_size,
        chunk_overlap=settings.fixed_chunk_overlap,
        separators=["\n\n", "\n", ". ", "! ", "? ", " ", ""],
        length_function=len,
    )
    chunks = splitter.split_text(text)
    return [c.strip() for c in chunks if len(c.strip()) > 20]


# ---------------------------------------------------------------------------
# Estrategia 2: Sentence-aware
# ---------------------------------------------------------------------------

def chunk_sentence(text: str, max_sentences: int = 5, overlap: int = 1) -> List[str]:
    """
    Agrupa oraciones en chunks de máximo `max_sentences` oraciones.
    Se aplica overlap de `overlap` oraciones entre chunks consecutivos.
    """
    sentences = split_sentences(text)
    if not sentences:
        return [text] if text.strip() else []

    chunks = []
    step = max(1, max_sentences - overlap)
    i = 0
    while i < len(sentences):
        window = sentences[i: i + max_sentences]
        chunk_text = " ".join(window).strip()
        if chunk_text:
            chunks.append(chunk_text)
        i += step

    return chunks


# ---------------------------------------------------------------------------
# Estrategia 3: Semantic chunking
# ---------------------------------------------------------------------------

def chunk_semantic(text: str, threshold: float = None) -> List[str]:
    """
    Divide el texto basándose en la similitud semántica entre oraciones adyacentes.
    Cuando la similitud cae por debajo de `threshold`, se inicia un nuevo chunk.
    Se aplica overlap de 1 oración.
    """
    if threshold is None:
        threshold = settings.semantic_threshold

    sentences = split_sentences(text)
    if len(sentences) <= 1:
        return [text] if text.strip() else []

    model = get_model()
    embeddings = model.encode(sentences, normalize_embeddings=True)

    chunks: List[str] = []
    current: List[str] = [sentences[0]]

    for i in range(1, len(sentences)):
        sim = float(cosine_similarity(
            embeddings[i - 1].reshape(1, -1),
            embeddings[i].reshape(1, -1),
        )[0][0])

        if sim >= threshold:
            current.append(sentences[i])
        else:
            chunks.append(" ".join(current).strip())
            # Overlap: el último elemento de current inicia el siguiente chunk
            current = [sentences[i - 1], sentences[i]]

    if current:
        chunks.append(" ".join(current).strip())

    return [c for c in chunks if len(c) > 20]


# ---------------------------------------------------------------------------
# Guardar chunks en MongoDB
# ---------------------------------------------------------------------------

def save_chunks(db, doc_id: str, chunks: List[str], strategy: str, tipo_doc: str, ciudad: str):
    col = db["document_chunks"]
    embeddings = embed(chunks)
    now = datetime.now(timezone.utc).isoformat()

    ops = []
    for idx, (texto, vec) in enumerate(zip(chunks, embeddings)):
        chunk_id = f"chunk_{strategy[:3]}_{doc_id}_{idx:04d}"
        doc = {
            "_id": chunk_id,
            "doc_id": doc_id,
            "chunk_index": idx,
            "estrategia_chunking": strategy,
            "texto": texto,
            "embedding": vec,
            "chunk_metadata": {
                "tipo_doc": tipo_doc,
                "ciudad": ciudad,
            },
            "modelo_embedding": settings.text_embedding_model,
            "fecha_ingesta": now,
        }
        from pymongo import UpdateOne
        ops.append(UpdateOne({"_id": chunk_id}, {"$set": doc}, upsert=True))

    if ops:
        col.bulk_write(ops, ordered=False)
    return len(ops)


def mark_doc_chunked(db, doc_id: str, strategy: str):
    """Registra en documents_repository que el doc ya tiene chunks de esta estrategia."""
    db["documents_repository"].update_one(
        {"_id": doc_id},
        {"$addToSet": {"chunking_aplicado": strategy}},
    )


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

STRATEGIES = {
    "fixed_size": chunk_fixed_size,
    "sentence": chunk_sentence,
    "semantic": chunk_semantic,
}

CIUDAD_DEFAULT = "Manizales"


def run_pipeline(strategy_filter: str = "all"):
    db = get_db()
    docs_col = db["documents_repository"]

    selected = (
        list(STRATEGIES.keys())
        if strategy_filter == "all"
        else [strategy_filter]
    )

    total_chunks = 0
    docs = list(docs_col.find({}, {"_id": 1, "contenido": 1, "tipo": 1, "chunking_aplicado": 1}))
    print(f"\n  Procesando {len(docs)} documentos con estrategias: {selected}")

    for doc in docs:
        doc_id = doc["_id"]
        texto = doc.get("contenido", "")
        tipo = doc.get("tipo", "general")
        ya_chunked = set(doc.get("chunking_aplicado", []))

        if not texto.strip():
            continue

        for strategy in selected:
            if strategy in ya_chunked:
                print(f"    [skip] {doc_id} — {strategy} ya procesado")
                continue

            chunk_fn = STRATEGIES[strategy]
            chunks = chunk_fn(texto)
            if not chunks:
                continue

            n = save_chunks(db, doc_id, chunks, strategy, tipo, CIUDAD_DEFAULT)
            mark_doc_chunked(db, doc_id, strategy)
            total_chunks += n
            print(f"    [OK] {doc_id:<40} {strategy:<12} → {n:>3} chunks")

    print(f"\n  Total chunks generados/actualizados: {total_chunks}")
    return total_chunks


# ---------------------------------------------------------------------------
# Búsqueda vectorial real con Atlas $vectorSearch
# ---------------------------------------------------------------------------


def build_filter(strategy: str | None, tipo_doc: str | None) -> dict:
    """Construye el filtro para $vectorSearch a partir de parámetros opcionales."""
    filtro: dict = {}
    if strategy:
        filtro["estrategia_chunking"] = strategy
    if tipo_doc:
        filtro["chunk_metadata.tipo_doc"] = tipo_doc
    return filtro


def vector_search(
    db,
    query: str,
    strategy: str | None = None,
    tipo_doc: str | None = None,
    top_k: int = 5,
) -> List[dict]:
    """
    Búsqueda vectorial real usando Atlas Vector Search ($vectorSearch).
    Requiere el índice 'vector_index_chunks' creado en Atlas UI.

    La función genera el embedding de la consulta y ejecuta una agregación
    con $vectorSearch, devolviendo los `top_k` chunks más similares junto
    con su score de similitud vectorial provisto por Atlas.
    """
    query_vec = embed([query])[0]

    pipeline: list[dict] = [
        {
            "$vectorSearch": {
                "index": "vector_index_chunks",
                "path": "embedding",
                "queryVector": query_vec,
                "numCandidates": 100,
                "limit": top_k,
                **({"filter": build_filter(strategy, tipo_doc)} if strategy or tipo_doc else {}),
            }
        },
        {
            "$project": {
                "_id": 1,
                "texto": 1,
                "doc_id": 1,
                "chunk_index": 1,
                "estrategia_chunking": 1,
                "chunk_metadata": 1,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    return list(db["document_chunks"].aggregate(pipeline))


def vector_search_images(
    db,
    media_id: str | None = None,
    top_k: int = 5,
) -> List[dict]:
    """
    Búsqueda vectorial por similitud de imágenes usando Atlas Vector Search.

    Requiere el índice 'vector_index_images' creado en Atlas UI sobre la
    colección image_embeddings.

    Si se proporciona un media_id, busca imágenes visualmente similares a esa
    imagen de referencia (usando su embedding). Si no, retorna las imágenes
    con mayor score (top_k globales).
    """
    if not media_id:
        return list(
            db["image_embeddings"].aggregate([
                {"$sample": {"size": top_k}},
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
                        "modelo": 1,
                        "url": "$media_info.url",
                        "tipo": "$media_info.tipo",
                        "property_id": "$media_info.property_id",
                        "score": 1,
                    }
                },
            ])
        )

    # Buscar el embedding de la imagen de referencia
    ref = db["image_embeddings"].find_one({"media_id": media_id})
    if not ref:
        return []

    query_vec = ref["embedding"]

    pipeline: list[dict] = [
        {
            "$vectorSearch": {
                "index": "vector_index_images",
                "path": "embedding",
                "queryVector": query_vec,
                "numCandidates": 100,
                "limit": top_k,
                "filter": {"media_id": {"$ne": media_id}},
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
                "modelo": 1,
                "url": "$media_info.url",
                "tipo": "$media_info.tipo",
                "property_id": "$media_info.property_id",
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    return list(db["image_embeddings"].aggregate(pipeline))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Pipeline de chunking y embeddings RAG Inmobiliaria")
    parser.add_argument(
        "--strategy",
        choices=["all", "fixed_size", "sentence", "semantic"],
        default="all",
        help="Estrategia de chunking a aplicar (default: all)",
    )
    args = parser.parse_args()

    print("=== Pipeline de Chunking y Embeddings ===")
    print(f"  Modelo: {settings.text_embedding_model} ({settings.text_embedding_dim} dims)")
    print(f"  Estrategia: {args.strategy}")

    run_pipeline(args.strategy)

    close()
    print("\n  Pipeline finalizado. Próximo paso: python api/main.py")


if __name__ == "__main__":
    main()
