"use strict";

/**
 * Script idempotente de carga de datos de prueba para MongoDB.
 *
 * Qué hace:
 * 1) Inserta o actualiza documentos base por _id (upsert).
 * 2) Mantiene consistencia entre documents_repository y document_chunks.
 * 3) No duplica registros aunque se ejecute múltiples veces.
 *
 * Requisitos:
 * - Ejecutar primero: npm run db:init
 * - Node.js 18+
 *
 * Variables de entorno opcionales:
 * - MONGODB_URI (default: mongodb://127.0.0.1:27017)
 * - DB_NAME     (default: Inmobiliaria_RAG_NoSQL)
 */

const { MongoClient, Int32 } = require("mongodb");

const MONGODB_URI = process.env.MONGODB_URI || "mongodb://127.0.0.1:27017";
const DB_NAME = process.env.DB_NAME || "Inmobiliaria_RAG_NoSQL";

/**
 * Upsert genérico por filtro: si existe actualiza, si no existe inserta.
 */
async function upsertByFilter(collection, filter, data) {
  const result = await collection.updateOne(
    filter,
    {
      $set: data
    },
    { upsert: true }
  );

  if (result.upsertedCount > 0) {
    console.log(`[upsert-insert] ${collection.collectionName} -> ${JSON.stringify(filter)}`);
  } else {
    console.log(`[upsert-update] ${collection.collectionName} -> ${JSON.stringify(filter)}`);
  }
}

async function main() {
  const client = new MongoClient(MONGODB_URI);

  try {
    await client.connect();
    const db = client.db(DB_NAME);

    console.log(`Cargando datos de prueba en: ${DB_NAME}`);

    // ==================================================
    // 1) USUARIO BASE
    // ==================================================
    await upsertByFilter(
      db.collection("users"),
      { _id: "u_001" },
      {
        _id: "u_001",
        nombre: "Juan Perez",
        email: "juan@email.com",
        roles: ["propietario"]
      }
    );

    // ==================================================
    // 2) PROPIEDAD BASE
    // ==================================================
    await upsertByFilter(
      db.collection("properties"),
      { _id: "prop_001" },
      {
        _id: "prop_001",
        owner_id: "u_001",
        titulo: "Apartamento moderno",
        ubicacion: {
          geo: {
            type: "Point",
            coordinates: [-75.52, 5.07]
          }
        }
      }
    );

    // ==================================================
    // 3) DOCUMENTOS FUENTE PARA RAG
    // ==================================================
    await upsertByFilter(
      db.collection("documents_repository"),
      { _id: "doc_001" },
      {
        _id: "doc_001",
        tipo: "descripcion_propiedad",
        contenido: "Apartamento amplio con excelente iluminacion...",
        origen_id: "prop_001",
        chunking_aplicado: ["semantic", "fixed_size", "sentence"]
      }
    );

    // Se agrega doc_002 para mantener consistencia con chunk_003.
    await upsertByFilter(
      db.collection("documents_repository"),
      { _id: "doc_002" },
      {
        _id: "doc_002",
        tipo: "contrato",
        contenido: "El arrendatario debe pagar antes del dia 5.",
        origen_id: "contract_001",
        chunking_aplicado: ["sentence"]
      }
    );

    // ==================================================
    // 4) CHUNKS VECTORIALES
    // ==================================================
    // chunk_index se guarda como Int32 para cumplir el validador bsonType: int.
    await upsertByFilter(
      db.collection("document_chunks"),
      { _id: "chunk_001" },
      {
        _id: "chunk_001",
        doc_id: "doc_001",
        chunk_index: new Int32(0),
        estrategia_chunking: "semantic",
        texto: "Apartamento con cocina abierta...",
        embedding: [0.12, -0.33, 0.91],
        chunk_metadata: {
          tipo_doc: "descripcion_propiedad",
          tema: "cocina",
          ciudad: "manizales"
        }
      }
    );

    await upsertByFilter(
      db.collection("document_chunks"),
      { _id: "chunk_002" },
      {
        _id: "chunk_002",
        doc_id: "doc_001",
        chunk_index: new Int32(1),
        estrategia_chunking: "fixed_size",
        texto: "Ubicado en zona residencial...",
        embedding: [0.45, -0.22, 0.88],
        chunk_metadata: {
          tipo_doc: "descripcion_propiedad",
          tema: "ubicacion",
          ciudad: "manizales"
        }
      }
    );

    await upsertByFilter(
      db.collection("document_chunks"),
      { _id: "chunk_003" },
      {
        _id: "chunk_003",
        doc_id: "doc_002",
        chunk_index: new Int32(0),
        estrategia_chunking: "sentence",
        texto: "El arrendatario debe pagar antes del dia 5.",
        embedding: [0.78, -0.09, 0.31],
        chunk_metadata: {
          tipo_doc: "contrato",
          ciudad: "manizales"
        }
      }
    );

    console.log("Carga de datos finalizada correctamente.");
  } finally {
    await client.close();
  }
}

main().catch((error) => {
  console.error("Error en carga de datos:", error);
  process.exitCode = 1;
});
