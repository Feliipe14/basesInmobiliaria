"""
regenerate_image_embeddings.py

Regenera los image_embeddings usando CLIP real (openai/clip-vit-base-patch32)
sobre las imágenes reales de Unsplash.

A diferencia de la versión anterior que usaba ruido simulado, este script:
1. Descarga cada imagen desde la URL guardada en media_assets
2. Genera el embedding visual con CLIP (512 dimensiones)
3. Guarda el embedding en image_embeddings

Requisitos:
    pip install transformers torch pillow requests

Ejecutar DESPUÉS de update_image_urls.py (las URLs deben ser reales):
    cd python
    python regenerate_image_embeddings.py
"""

import sys
import io
import math
from datetime import datetime, timezone

sys.path.insert(0, ".")
from database import get_db, close

import requests
from PIL import Image
import torch
import numpy as np


# ---------------------------------------------------------------------------
# Cargar modelo CLIP una sola vez
# ---------------------------------------------------------------------------

print("[INFO] Cargando modelo CLIP (openai/clip-vit-base-patch32)...")
from transformers import CLIPModel, CLIPProcessor

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[INFO] Dispositivo: {DEVICE}")

clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(DEVICE)
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
clip_model.eval()
print("[INFO] CLIP cargado correctamente.")


# ---------------------------------------------------------------------------
# Funciones de embedding (copiadas del notebook del profesor)
# ---------------------------------------------------------------------------

def embed_image_clip(image: Image.Image) -> list[float]:
    """
    Embedding visual con CLIP. Dimensión: 512.
    Usa la misma lógica que el notebook del profesor para evitar errores.
    """
    image = image.convert("RGB")
    inputs = clip_processor(images=image, return_tensors="pt").to(DEVICE)

    with torch.no_grad():
        outputs = clip_model.vision_model(pixel_values=inputs["pixel_values"])

        if hasattr(outputs, "pooler_output") and outputs.pooler_output is not None:
            pooled = outputs.pooler_output
        else:
            pooled = outputs.last_hidden_state[:, 0, :]

        image_features = clip_model.visual_projection(pooled)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)

    return image_features[0].cpu().numpy().astype(np.float32).tolist()


def descargar_imagen(url: str, timeout: int = 15) -> Image.Image | None:
    """
    Descarga una imagen desde una URL.
    Retorna un objeto PIL.Image o None si falla.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; RAG-Inmobiliaria/1.0)"
        }
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content))
        return img
    except Exception as e:
        print(f"    [ERROR] No se pudo descargar {url}: {e}")
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    db = get_db()
    emb_col = db["image_embeddings"]
    media_col = db["media_assets"]

    total = media_col.count_documents({})
    print(f"[INFO] {total} media_assets para procesar...")

    ok_count = 0
    fail_count = 0
    skip_count = 0

    for media in media_col.find({}):
        mid = media["_id"]
        url = media.get("url", "")
        emb_id = f"img_emb_{mid}"

        if not url or "unsplash" not in url:
            print(f"  [SKIP] {mid:<25s} URL no válida: {url}")
            skip_count += 1
            continue

        print(f"  [Bajando] {mid:<25s} ...", end=" ", flush=True)
        img = descargar_imagen(url)

        if img is None:
            fail_count += 1
            continue

        vec = embed_image_clip(img)
        print(f"embedding OK (dim={len(vec)})")

        emb_col.update_one(
            {"_id": emb_id},
            {"$set": {
                "media_id": mid,
                "embedding": vec,
                "modelo": "clip-vit-base-patch32",
                "url_origen": url,
                "actualizado_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )
        ok_count += 1

    print(f"\n[RESUMEN]")
    print(f"  OK:     {ok_count}")
    print(f"  Fallos: {fail_count}")
    print(f"  Saltados: {skip_count}")
    print(f"  Total:  {total}")

    if ok_count > 1:
        _quick_verify(db)

    close()


def _quick_verify(db):
    """Verifica que los embeddings tengan sentido: mismas categorías deben ser similares."""
    embs = list(db["image_embeddings"].find({}, {"media_id": 1, "embedding": 1}))
    if len(embs) < 2:
        return

    # Agrupar por sufijo (_01=fachada, _02=sala, _03=habitacion)
    grupos = {"_01": [], "_02": [], "_03": []}
    for e in embs:
        for suf in grupos:
            if e["media_id"].endswith(suf):
                grupos[suf].append(e["embedding"])
                break

    def cos(a, b):
        a, b = np.array(a), np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def avg_cos(v1_list, v2_list):
        if not v1_list or not v2_list:
            return 0.0
        scores = []
        for a in v1_list:
            for b in v2_list:
                scores.append(cos(a, b))
        return sum(scores) / len(scores) if scores else 0.0

    print("\n[VERIFICACIÓN] Similitud coseno media entre grupos:")
    etiquetas = {"_01": "fachada", "_02": "sala", "_03": "habitacion"}
    for s1 in grupos:
        for s2 in grupos:
            sim = avg_cos(grupos[s1], grupos[s2])
            print(f"  {etiquetas[s1]:12s} vs {etiquetas[s2]:12s}: {sim:.4f}")


if __name__ == "__main__":
    main()
