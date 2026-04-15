"use strict";

require("dotenv").config();

/**
 * Script idempotente de inicialización para MongoDB.
 *
 * Qué hace:
 * 1) Crea (si no existen) las colecciones del modelo.
 * 2) Aplica/actualiza validadores JSON Schema en colecciones objetivo.
 * 3) Crea índices necesarios (incluyendo únicos, texto y geoespaciales).
 *
 * Requisitos:
 * - Node.js 18+
 * - npm install mongodb
 *
 * Variables de entorno opcionales:
 * - MONGODB_URI (default: mongodb://127.0.0.1:27017)
 * - DB_NAME     (default: Inmobiliaria_RAG_NoSQL)
 */

const { MongoClient } = require("mongodb");

const MONGODB_URI = process.env.MONGODB_URI || "mongodb://127.0.0.1:27017";
const DB_NAME = process.env.DB_NAME || "Inmobiliaria_RAG_NoSQL";

/**
 * Crea la colección si no existe y aplica el validador.
 * Si ya existe, usa collMod para actualizar validador sin fallar.
 */
async function ensureCollectionWithValidator(db, name, validator) {
  const exists = await db
    .listCollections({ name }, { nameOnly: true })
    .hasNext();

  if (!exists) {
    await db.createCollection(name, { validator });
    console.log(`[createCollection] ${name} creada con validador.`);
    return;
  }

  await db.command({ collMod: name, validator, validationLevel: "strict" });
  console.log(`[collMod] ${name} ya existía; validador actualizado.`);
}

/**
 * Crea una colección simple solo si no existe.
 */
async function ensureCollection(db, name) {
  const exists = await db
    .listCollections({ name }, { nameOnly: true })
    .hasNext();
  if (!exists) {
    await db.createCollection(name);
    console.log(`[createCollection] ${name} creada.`);
  } else {
    console.log(`[skip] ${name} ya existe.`);
  }
}

/**
 * Crea índice de forma idempotente.
 * createIndex no falla si el índice ya existe con la misma definición.
 */
async function ensureIndex(collection, keys, options = {}) {
  try {
    const indexName = await collection.createIndex(keys, options);
    console.log(`[createIndex] ${collection.collectionName} -> ${indexName}`);
  } catch (error) {
    // Evita romper la ejecución cuando ya existe un índice equivalente con otra configuración/nombre.
    const conflictNames = new Set([
      "IndexOptionsConflict",
      "IndexKeySpecsConflict",
      "IndexAlreadyExists",
    ]);

    if (conflictNames.has(error.codeName)) {
      const configuredName =
        options && options.name ? options.name : "(sin nombre)";
      console.warn(
        `[index-skip] ${collection.collectionName} -> ${configuredName}; conflicto benigno: ${error.codeName}`,
      );
      return;
    }

    throw error;
  }
}

/**
 * Intenta crear un índice vectorial "simulado" según el script original.
 * Si el servidor no soporta la clave "cosine" en createIndex clásico, aplica fallback a índice ascendente.
 */
async function ensureSimulatedVectorIndex(collection) {
  try {
    await ensureIndex(
      collection,
      { embedding: "cosine" },
      { name: "ix_document_chunks_embedding_cosine" },
    );
  } catch (error) {
    console.warn(
      `[vector-fallback] ${collection.collectionName}; 'cosine' no soportado en createIndex clásico. Se usa índice ascendente.`,
    );
    await ensureIndex(
      collection,
      { embedding: 1 },
      { name: "ix_document_chunks_embedding_simulated" },
    );
  }
}

async function main() {
  const client = new MongoClient(MONGODB_URI);

  try {
    await client.connect();
    const db = client.db(DB_NAME);

    console.log("Conexión exitosa a MongoDB Atlas");

    // Verificación real
    const collections = await db.listCollections().toArray();
    console.log("Colecciones disponibles:");
    console.log(collections.map((c) => c.name));

    console.log(`Inicializando base de datos: ${DB_NAME}`);

    // ==================================================
    // 1) COLECCIONES CON VALIDADORES
    // ==================================================

    await ensureCollectionWithValidator(db, "users", {
      $jsonSchema: {
        bsonType: "object",
        required: ["email", "roles"],
        properties: {
          email: {
            bsonType: "string",
            pattern: "^.+@.+$",
          },
          roles: {
            bsonType: "array",
            items: {
              enum: ["propietario", "arrendatario", "agente"],
            },
          },
        },
      },
    });

    await ensureCollectionWithValidator(db, "properties", {
      $jsonSchema: {
        bsonType: "object",
        required: ["owner_id", "ubicacion"],
        properties: {
          owner_id: { bsonType: "string" },
          ubicacion: {
            bsonType: "object",
            required: ["geo"],
            properties: {
              geo: {
                bsonType: "object",
                required: ["type", "coordinates"],
              },
            },
          },
        },
      },
    });

    await ensureCollectionWithValidator(db, "document_chunks", {
      $jsonSchema: {
        bsonType: "object",
        required: [
          "doc_id",
          "chunk_index",
          "estrategia_chunking",
          "texto",
          "embedding",
        ],
        properties: {
          doc_id: { bsonType: "string" },
          chunk_index: { bsonType: "int" },
          estrategia_chunking: {
            enum: ["fixed_size", "semantic", "sentence"],
          },
          texto: { bsonType: "string" },
          embedding: {
            bsonType: "array",
            items: { bsonType: "double" },
          },
        },
      },
    });

    // ==================================================
    // 2) COLECCIONES OPERATIVAS (SIN VALIDADOR)
    // ==================================================

    const operationalCollections = [
      "agencies",
      "listings",
      "contracts",
      "chat_sessions",
      "media_assets",
      "maintenance_requests",
      "reviews",
      "documents_repository",
      "image_embeddings",
      "rag_queries_logs",
      "rag_evaluations",
    ];

    for (const name of operationalCollections) {
      await ensureCollection(db, name);
    }

    // ==================================================
    // 3) ÍNDICES
    // ==================================================

    // users: email único
    await ensureIndex(
      db.collection("users"),
      { email: 1 },
      { unique: true, name: "ux_users_email" },
    );

    // properties: índice geoespacial
    await ensureIndex(
      db.collection("properties"),
      { "ubicacion.geo": "2dsphere" },
      { name: "ix_properties_ubicacion_geo_2dsphere" },
    );

    // documents_repository: búsqueda de texto completo
    await ensureIndex(
      db.collection("documents_repository"),
      { contenido: "text" },
      { name: "ix_documents_repository_contenido_text" },
    );

    // document_chunks: índice vectorial "simulado" del documento original.
    // Nota: para búsqueda vectorial real en Atlas, usar Vector Search Index (no createIndex clásico).
    await ensureSimulatedVectorIndex(db.collection("document_chunks"));

    // document_chunks: índices híbridos por metadatos
    await ensureIndex(
      db.collection("document_chunks"),
      {
        "chunk_metadata.tipo_doc": 1,
        "chunk_metadata.ciudad": 1,
      },
      { name: "ix_document_chunks_tipo_doc_ciudad" },
    );

    // listings: filtro por tipo y precio
    await ensureIndex(
      db.collection("listings"),
      { tipo: 1, precio: 1 },
      { name: "ix_listings_tipo_precio" },
    );

    // chat_sessions: relación con listing
    await ensureIndex(
      db.collection("chat_sessions"),
      { listing_id: 1 },
      { name: "ix_chat_sessions_listing_id" },
    );

    console.log("Inicialización finalizada correctamente.");
  } finally {
    await client.close();
  }
}

main().catch((error) => {
  console.error("Error en inicialización:", error);
  process.exitCode = 1;
});
