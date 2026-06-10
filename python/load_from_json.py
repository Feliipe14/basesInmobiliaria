"""
Script de carga de datos desde archivos JSON a MongoDB.

Permite importar documentos desde JSON externos para poblar o
enriquecer las colecciones del sistema RAG inmobiliario.

Uso:
    python load_from_json.py datos_ejemplo.json

Formato esperado del JSON:
    {
        "coleccion": "properties",
        "datos": [ { ... }, { ... } ]
    }

    donde "coleccion" es una de las colecciones del sistema
    y "datos" es un arreglo de documentos a insertar.
"""

import sys
import json
import os
from pymongo import UpdateOne

sys.path.insert(0, ".")
from database import get_db, close


def cargar_json(ruta_archivo: str):
    """Carga un archivo JSON y lo inserta en MongoDB.

    El JSON debe tener el formato:
    {
        "coleccion": "nombre_coleccion",
        "datos": [ { "_id": "...", ... }, ... ]
    }

    Usa upsert para ser idempotente: si el documento ya existe
    por su _id, lo actualiza; si no, lo crea.
    """
    if not os.path.isfile(ruta_archivo):
        print(f"ERROR: El archivo '{ruta_archivo}' no existe.")
        return False

    with open(ruta_archivo, "r", encoding="utf-8") as f:
        contenido = json.load(f)

    coleccion = contenido.get("coleccion")
    datos = contenido.get("datos", [])

    if not coleccion:
        print("ERROR: El JSON debe tener un campo 'coleccion'.")
        return False

    if not datos:
        print("El JSON no contiene datos en el campo 'datos'.")
        return False

    # Colecciones validas del sistema
    colecciones_validas = [
        "users", "agencies", "properties", "media_assets",
        "listings", "contracts", "reviews", "maintenance_requests",
        "documents_repository", "document_chunks", "image_embeddings",
        "rag_queries_logs", "rag_evaluations", "chat_sessions",
    ]

    if coleccion not in colecciones_validas:
        print(f"ADVERTENCIA: '{coleccion}' no esta en la lista de colecciones conocidas.")
        print(f"Colecciones validas: {', '.join(colecciones_validas)}")
        confirmar = input("Continuar de todas formas? (s/N): ")
        if confirmar.lower() != "s":
            return False

    db = get_db()
    col = db[coleccion]

    operaciones = []
    for doc in datos:
        doc_id = doc.get("_id")
        if not doc_id:
            print(f"  Saltando documento sin _id: {str(doc)[:60]}")
            continue
        operaciones.append(
            UpdateOne(
                {"_id": doc_id},
                {"$set": doc},
                upsert=True,
            )
        )

    if operaciones:
        resultado = col.bulk_write(operaciones)
        print(f"  Coleccion: {coleccion}")
        print(f"  Documentos procesados: {len(operaciones)}")
        print(f"  Insertados: {resultado.upserted_count}")
        print(f"  Actualizados: {resultado.modified_count}")
        print(f"  Coincidieron (sin cambios): {resultado.matched_count - resultado.modified_count}")
    else:
        print("  No se encontraron documentos validos para procesar.")

    return True


def main():
    if len(sys.argv) < 2:
        print("Uso: python load_from_json.py <archivo.json>")
        print("")
        print("Ejemplos:")
        print("  python load_from_json.py datos_ejemplo.json")
        print("  python load_from_json.py data/mis_datos.json")
        return

    ruta = sys.argv[1]
    print(f"Cargando datos desde: {ruta}")
    print("-" * 40)
    exito = cargar_json(ruta)
    print("-" * 40)
    if exito:
        print("Carga completada.")
    else:
        print("Carga fallida.")
    close()


if __name__ == "__main__":
    main()
