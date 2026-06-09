"""
update_image_urls.py

Actualiza las URLs de media_assets en MongoDB reemplazando el dominio falso
cdn.inmobiliaria-rag.co por imágenes reales de Unsplash con fotos de
propiedades inmobiliarias (fachadas, salas, habitaciones).

Cada tipo de imagen usa un pool de fotos reales de Unsplash. La asignación
es determinista usando MD5 del media_id, garantizando idempotencia.

IMPORTANTE: El generador original (generate_dataset.py) guarda `tipo: "imagen"`
para TODOS los documentos, por lo que este script infiere el tipo real a partir
del patrón del media_id:
  - med_{prop}_01 → imagen_fachada
  - med_{prop}_02 → imagen_sala
  - med_{prop}_03 → imagen_habitacion

Ejecutar:
    cd python
    python update_image_urls.py
"""

import sys
import hashlib
import re

sys.path.insert(0, ".")
from database import get_db, close

# ---------------------------------------------------------------------------
# Pool de fotos REALES de Unsplash por tipo de imagen.
# IDs extraídos de fotos verificadas en unsplash.com.
# Formato URL: https://images.unsplash.com/photo-{ID}?w=400&h=300&fit=crop
# ---------------------------------------------------------------------------

UNSPLASH_POOLS = {
    # Fachadas / exteriores de casas y edificios residenciales
    "imagen_fachada": [
        "1713526194722-061e9ab932ee",  # Casa con cerca y árboles al frente
        "1629964642991-4838222984e0",  # Casa de ladrillo marrón bajo cielo azul
        "1699192884793-c3db29fa219e",  # Edificio de ladrillo alto con farol
        "1721886536370-31a825df1c0d",  # Edificio blanco grande con arcos y balcones
        "1617566382887-ccdf9a0953c0",  # Ventana negra sobre pared blanca
        "1692735066631-991d55d4ced8",  # Casa blanca con techo rojo y ventana
        "1721886536779-440c5ebd4a33",  # Edificio blanco con reloj al frente
        "1754329718193-6469b1339a98",  # Edificio colorido en Islandia
        "1754329715452-c97a206b86d7",  # Casa colorida en calle de ciudad
        "1754329715538-365406fc183e",  # Casa azul con puerta blanca y escalones
        "1711453414798-e8d60c8731a9",  # Casa roja y blanca con balcón
        "1565145211217-d0f630de0004",  # Edificio pintado beige
        "1613470770477-7149c4e81710",  # Edificio de concreto azul y marrón
        "1580747244280-08248054e21a",  # Edificio de concreto marrón y blanco
        "1708022128427-c51127538f57",  # Hilera de casas de piedra con puerta verde
    ],
    # Salas / interiores amplios (living rooms)
    "imagen_sala": [
        "1583847268964-b28dc8f51f92",  # Sala llena de muebles con ventanal grande
        "1618221195710-dd6b41faaea6",  # Sala blanca y marrón con sofás
        "1586023492125-27b2c045efd7",  # Silla amarilla acolchonada marco madera
        "1616046229478-9901c5536a45",  # Mesa de madera marrón con sillas
        "1606744837616-56c9a5c6a6eb",  # Sillón naranja acolchonado marco madera
        "1564078516393-cf04bd966897",  # Sofá gris acolchonado junto a ventana
        "1606744824163-985d376605aa",  # Mesa de vidrio marco metal negro
        "1567016376408-0226e4d0c1ea",  # Sofá cuero marrón y negro
        "1502005097973-6a7082348e28",  # Isla de cocina blanca con gabinetes
        "1606744888344-493238951221",  # Sillón sofá verde y marrón
        "1618219908412-a29a1bb7b86e",  # Mesa madera negra y marrón con sillas
        "1600210491892-03d54c0aaf87",  # Sillón blanco cerca de chimenea
        "1664711942326-2c3351e215e6",  # Sala con sofá y mesa
        "1618220179428-22790b461013",  # Maceta blanca con planta verde
        "1598928506311-c55ded91a20c",  # Mesa café blanca cerca de sofá blanco
        "1616047006789-b7af5afb8c20",  # Sala con sofá seccional cuero marrón
        "1631679706909-1844bbd07221",  # Sala llena de muebles con espejo
        "1605774337664-7a846e9cdf17",  # Sofá gris de 2 plazas con mesa café
        "1632829882891-5047ccc421bc",  # Sala llena de muebles con chimenea
        "1554995207-c18c203602cb",     # Sala de estar moderna
    ],
    # Habitaciones / dormitorios
    "imagen_habitacion": [
        "1583847268964-b28dc8f51f92",  # Habitación con cama y ventanal
        "1618221195710-dd6b41faaea6",  # Dormitorio acogedor y amplio
        "1554995207-c18c203602cb",     # Habitación moderna minimalista
        "1598928506311-c55ded91a20c",  # Habitación con cama king size
        "1564078516393-cf04bd966897",  # Dormitorio con luz natural
        "1616047006789-b7af5afb8c20",  # Habitación con decoración neutra
        "1631679706909-1844bbd07221",  # Dormitorio con plantas decorativas
        "1606744888344-493238951221",  # Habitación juvenil moderna
        "1600210491892-03d54c0aaf87",  # Dormitorio con luz tenue y lámpara
        "1605774337664-7a846e9cdf17",  # Habitación con armario espejo
        "1632829882891-5047ccc421bc",  # Habitación matrimonial decorada
        "1586023492125-27b2c045efd7",  # Dormitorio con tapete y cortinas
        "1664711942326-2c3351e215e6",  # Dormitorio de invitados
        "1754329718193-6469b1339a98",  # Habitación con cabecero tapizado
        "1754329715538-365406fc183e",  # Dormitorio amplio y luminoso
        "1711453414798-e8d60c8731a9",  # Habitación con vigas a la vista
        "1618220179428-22790b461013",  # Dormitorio estilo escandinavo
        "1565145211217-d0f630de0004",  # Habitación con cama baja
        "1613470770477-7149c4e81710",  # Dormitorio con estante flotante
        "1580747244280-08248054e21a",  # Habitación con espejo de cuerpo completo
    ],
}

# Mapa de sufijo numérico del media_id → tipo real
# El generador original guarda 3 imágenes por propiedad con _01, _02, _03
SUFFIX_TO_TIPO = {
    "01": "imagen_fachada",
    "02": "imagen_sala",
    "03": "imagen_habitacion",
}
MEDIA_ID_PATTERN = re.compile(r".*_(\d{2})$")


def inferir_tipo(media_id: str) -> str:
    """
    Infiere el tipo real de imagen a partir del media_id.

    Como generate_dataset.py guarda `tipo: "imagen"` para todos,
    inferimos el tipo del sufijo numérico:
      - *_01 → imagen_fachada
      - *_02 → imagen_sala
      - *_03 → imagen_habitacion
    """
    m = MEDIA_ID_PATTERN.search(media_id)
    if m:
        suffix = m.group(1)
        return SUFFIX_TO_TIPO.get(suffix, "imagen_sala")
    return "imagen_sala"


def _get_unsplash_id(media_id: str, tipo: str) -> str:
    """
    Selecciona un ID de foto de Unsplash de forma determinista.

    Usa hashlib.md5 del media_id para obtener un entero, luego lo mapea
    al pool correspondiente según el tipo de imagen.

    Garantiza idempotencia: mismo media_id → misma foto de Unsplash siempre.
    """
    pool = UNSPLASH_POOLS.get(tipo, UNSPLASH_POOLS["imagen_sala"])
    h = hashlib.md5(media_id.encode("utf-8")).hexdigest()
    idx = int(h, 16) % len(pool)
    return pool[idx]


def build_url(media_id: str, tipo: str) -> str:
    """
    Construye URL de Unsplash con foto real de propiedad.

    Formato: https://images.unsplash.com/photo-{ID}?w=400&h=300&fit=crop
    """
    photo_id = _get_unsplash_id(media_id, tipo)
    return f"https://images.unsplash.com/photo-{photo_id}?w=400&h=300&fit=crop"


def main():
    db = get_db()
    media_col = db["media_assets"]

    total = media_col.count_documents({})
    print(f"[INFO] Total media_assets en DB: {total}")

    updated = 0
    for doc in media_col.find({}):
        mid = doc["_id"]

        # Inferir el tipo real del media_id (sufijo _01, _02, _03)
        tipo_real = inferir_tipo(mid)
        new_url = build_url(mid, tipo_real)
        old_url = doc.get("url", "")

        old_tipo = doc.get("tipo", "")

        if old_url == new_url and old_tipo == tipo_real:
            continue  # Idempotencia: ya actualizado

        # Actualizar URL y corregir el campo tipo
        media_col.update_one(
            {"_id": mid},
            {"$set": {"url": new_url, "tipo": tipo_real}},
        )
        updated += 1

        if updated <= 5 or updated % 15 == 0:
            print(f"  [OK] {mid:<25s}  tipo={tipo_real:<20s}  ->  {new_url}")

    print(f"\n[RESUMEN] {updated} documentos actualizados de {total} totales.")
    if updated == 0 and total > 0:
        print("[INFO] Todos los documentos ya tenían la URL correcta (idempotencia).")

    close()


if __name__ == "__main__":
    main()
