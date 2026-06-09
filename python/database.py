"""Singleton de conexion MongoDB."""

from pymongo import MongoClient
from pymongo.database import Database

from config import settings

# Variable privada que almacena la unica instancia del cliente MongoDB
# **patron_singleton**: garantiza una sola conexion a base de datos en toda la aplicacion
_client: MongoClient | None = None


def get_client() -> MongoClient:
    # **responsabilidad**: retorna el cliente MongoDB, creandolo solo la primera vez
    global _client
    if _client is None:
        _client = MongoClient(settings.mongodb_uri)
    return _client


def get_db() -> Database:
    # **responsabilidad**: obtiene la base de datos especifica del proyecto desde el cliente
    return get_client()[settings.db_name]


def close():
    # **responsabilidad**: cierra la conexion a MongoDB y limpia la variable global
    global _client
    if _client:
        _client.close()
        _client = None
