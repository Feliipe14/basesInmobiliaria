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

    await ensureCollectionWithValidator(db, "contracts", {
      $jsonSchema: {
        bsonType: "object",
        required: ["listing_id", "arrendador_id", "arrendatario_id"],
        properties: {
          listing_id:       { bsonType: "string" },
          arrendador_id:    { bsonType: "string" },
          arrendatario_id:  { bsonType: "string" },
          estado: {
            enum: ["activo", "finalizado", "cancelado"],
          },
          fecha_inicio:      { bsonType: ["date", "string"] },
          fecha_vencimiento: { bsonType: ["date", "string"] },
          clausulas: {
            bsonType: "array",
            items: {
              bsonType: "object",
              required: ["titulo", "descripcion"],
              properties: {
                titulo:      { bsonType: "string" },
                descripcion: { bsonType: "string" },
              },
            },
          },
        },
      },
    });

    await ensureCollectionWithValidator(db, "documents_repository", {
      $jsonSchema: {
        bsonType: "object",
        required: ["tipo", "contenido", "origen_id"],
        properties: {
          tipo:     { bsonType: "string" },
          contenido: { bsonType: "string" },
          origen_id: { bsonType: "string" },
          origen_tipo: {
            enum: ["property", "contract", "chat_session", "general"],
          },
          chunking_aplicado: {
            bsonType: "array",
            items: { bsonType: "string" },
          },
        },
      },
    });

    await ensureCollectionWithValidator(db, "rag_evaluations", {
      $jsonSchema: {
        bsonType: "object",
        required: ["rag_query_id"],
        properties: {
          rag_query_id:     { bsonType: "string" },
          relevancia:       { bsonType: ["double", "int"] },
          precision:        { bsonType: ["double", "int"] },
          faithfulness:     { bsonType: ["double", "int"] },
          answer_relevancy: { bsonType: ["double", "int"] },
          context_recall:   { bsonType: ["double", "int"] },
          modelo_eval:      { bsonType: "string" },
          fecha:            { bsonType: ["date", "string"] },
        },
      },
    });

    // ==================================================
    // 2) COLECCIONES OPERATIVAS (SIN VALIDADOR)
    // ==================================================

    const operationalCollections = [
      "agencies",
      "listings",
      "chat_sessions",
      "media_assets",
      "maintenance_requests",
      "reviews",
      "image_embeddings",
      "rag_queries_logs",
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

    // contracts: consulta por estado + fecha de vencimiento
    await ensureIndex(
      db.collection("contracts"),
      { estado: 1, fecha_vencimiento: 1 },
      { name: "ix_contracts_estado_fecha_vencimiento" },
    );

    // documents_repository: búsqueda por origen_id y tipo
    await ensureIndex(
      db.collection("documents_repository"),
      { origen_id: 1, tipo: 1 },
      { name: "ix_documents_repository_origen_tipo" },
    );

    // documents_repository: texto completo sobre contenido
    await ensureIndex(
      db.collection("documents_repository"),
      { contenido: "text" },
      { name: "ix_documents_repository_contenido_text", default_language: "spanish" },
    );

    // rag_queries_logs: timestamp para ordenar historial
    await ensureIndex(
      db.collection("rag_queries_logs"),
      { timestamp: -1 },
      { name: "ix_rag_queries_logs_timestamp" },
    );

    // image_embeddings: relación con media_asset
    await ensureIndex(
      db.collection("image_embeddings"),
      { media_id: 1 },
      { name: "ix_image_embeddings_media_id" },
    );

    // reviews: target_property_id para listar reseñas por propiedad
    await ensureIndex(
      db.collection("reviews"),
      { target_property_id: 1 },
      { name: "ix_reviews_target_property_id" },
    );

    /*
     * NOTA — Índice Vectorial (Atlas Vector Search):
     * El índice para document_chunks.embedding y image_embeddings.embedding
     * NO se crea con db.createIndex(). Se configura en:
     *   Atlas UI → tu clúster → Search → Create Search Index → JSON Editor
     *
     * Definición para document_chunks (384 dimensiones, all-MiniLM-L6-v2):
     * {
     *   "fields": [{
     *     "type": "vector",
     *     "path": "embedding",
     *     "numDimensions": 384,
     *     "similarity": "cosine"
     *   }]
     * }
     *
     * Definición para image_embeddings (512 dimensiones, CLIP):
     * {
     *   "fields": [{
     *     "type": "vector",
     *     "path": "embedding",
     *     "numDimensions": 512,
     *     "similarity": "cosine"
     *   }]
     * }
     *
     * Requiere clúster M10+. En M0 (gratuito), la búsqueda vectorial se
     * hace manualmente calculando similitud coseno en el cliente (Python).
     * Ver: python/chunking_pipeline.py → función vector_search_manual()
     */

    console.log("Inicialización finalizada correctamente.");
  } finally {
    await client.close();
  }
}

main().catch((error) => {
  console.error("Error en inicialización:", error);
  process.exitCode = 1;
});
