"""
Módulo de evaluación RAGAS — Sistema RAG Inmobiliaria Manizales.

Evalúa las 3 estrategias de chunking con métricas reales de RAGAS:
  - faithfulness:       ¿la respuesta está fundamentada en el contexto recuperado?
  - answer_relevancy:   ¿la respuesta es relevante para la pregunta planteada?
  - context_recall:     ¿el contexto recuperado contiene la respuesta esperada (ground truth)?

Uso desde CLI:
    cd python
    python evaluacion_ragas.py [--strategy all|fixed_size|sentence|semantic] [--top-k 5]

Uso como módulo (API):
    from evaluacion_ragas import run_ragas_evaluation
    summary = run_ragas_evaluation(strategies=["semantic"], top_k=5)
"""

import sys
import math
import asyncio
import hashlib
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from groq import Groq

sys.path.insert(0, ".")
from config import settings
from database import get_db, close
from chunking_pipeline import vector_search, get_model


# ---------------------------------------------------------------------------
# System prompt (idéntico al de api/main.py para coherencia)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "Eres un asistente experto en bienes raíces en Colombia, especializado en el mercado "
    "inmobiliario de Manizales, Caldas. "
    "Respondes preguntas sobre propiedades, contratos de arrendamiento, reglamentos de "
    "copropiedad y el proceso de arrendamiento en Colombia. "
    "Basas tus respuestas ÚNICAMENTE en el contexto proporcionado. Si la información no "
    "está en el contexto, indícalo claramente. "
    "Responde siempre en español colombiano, de manera profesional y concisa. "
    "Cuando el contexto lo permita, menciona detalles específicos como precios en COP, "
    "barrios de Manizales o cláusulas contractuales."
)


# ---------------------------------------------------------------------------
# Dataset de Ground Truth (22 pares pregunta-respuesta ideal)
# Cubre todos los temas del dominio inmobiliario requeridos
# ---------------------------------------------------------------------------

GROUND_TRUTH: List[Dict[str, str]] = [
    # --- Políticas de mascotas (2) ---
    {
        "question": "¿Se permiten mascotas en el apartamento?",
        "ground_truth": (
            "La política de mascotas varía según cada propiedad. Algunas propiedades en "
            "Inmobiliaria RAG Manizales permiten mascotas pequeñas con depósito adicional "
            "y autorización escrita del arrendador, mientras que otras tienen restricciones "
            "totales de acuerdo al reglamento de propiedad horizontal."
        ),
    },
    {
        "question": "¿Pueden vivir mascotas en los conjuntos residenciales de Manizales?",
        "ground_truth": (
            "El reglamento de copropiedad determina si se permiten mascotas en el conjunto. "
            "Generalmente se permiten animales domésticos pequeños siempre que no generen "
            "ruidos o daños a las zonas comunes, y el propietario debe acatar las normas "
            "del reglamento de propiedad horizontal."
        ),
    },
    # --- Valores de arriendo y formas de pago (3) ---
    {
        "question": "¿Cuál es el valor del arriendo mensual?",
        "ground_truth": (
            "El valor del canon de arrendamiento depende de cada propiedad. Los apartamentos "
            "en Manizales pueden oscilar entre $800.000 y $3.000.000 COP mensuales según "
            "el sector, el número de habitaciones y los servicios incluidos."
        ),
    },
    {
        "question": "¿Cuáles son las formas de pago del arriendo?",
        "ground_truth": (
            "El canon de arrendamiento se paga mensualmente por anticipado, dentro de los "
            "primeros cinco días de cada mes. Se puede pagar mediante transferencia bancaria, "
            "consignación o efectivo según lo acordado en el contrato. En caso de mora se "
            "generan intereses de acuerdo a la ley colombiana."
        ),
    },
    {
        "question": "¿Cada cuánto se incrementa el valor del arriendo?",
        "ground_truth": (
            "Según la ley colombiana, el incremento anual del canon de arrendamiento no "
            "puede superar el IPC (Índice de Precios al Consumidor) del año anterior. El "
            "arrendador debe notificar al arrendatario con al menos tres meses de anticipación."
        ),
    },
    # --- Número de habitaciones (2) ---
    {
        "question": "¿Cuántas habitaciones tiene la propiedad?",
        "ground_truth": (
            "El número de habitaciones varía según el inmueble. Los apartamentos disponibles "
            "en Inmobiliaria RAG Manizales generalmente tienen entre 1 y 4 habitaciones, con "
            "la mayoría de las propiedades contando con 2 o 3 alcobas."
        ),
    },
    {
        "question": "¿Cuántos baños tiene el apartamento?",
        "ground_truth": (
            "Los apartamentos en el portafolio de Inmobiliaria RAG Manizales generalmente "
            "cuentan con 1 o 2 baños. Los apartamentos de 3 o más habitaciones suelen tener "
            "baño principal y baño social."
        ),
    },
    # --- Cláusulas contractuales (2) ---
    {
        "question": "¿Qué incluye el contrato de arrendamiento?",
        "ground_truth": (
            "El contrato de arrendamiento incluye cláusulas sobre el canon mensual, duración "
            "del contrato (generalmente 12 meses), depósito de garantía, condiciones de "
            "mantenimiento, normas de convivencia, causales de terminación y procedimiento "
            "para la entrega del inmueble."
        ),
    },
    {
        "question": "¿Cuánto tiempo dura el contrato de arrendamiento?",
        "ground_truth": (
            "Los contratos de arrendamiento en Colombia generalmente tienen una duración de "
            "12 meses con opción de renovación automática. Cualquiera de las partes puede "
            "dar por terminado el contrato con 3 meses de anticipación mediante comunicación "
            "escrita."
        ),
    },
    # --- Ubicación de propiedades (2) ---
    {
        "question": "¿Cuál es la ubicación exacta del inmueble?",
        "ground_truth": (
            "Las propiedades de Inmobiliaria RAG se encuentran en diferentes barrios de "
            "Manizales, Caldas, incluyendo sectores como El Cable, La Enea, Chipre, Palermo "
            "y Centro. Cada propiedad tiene su dirección específica indicada en el anuncio."
        ),
    },
    {
        "question": "¿En qué barrios de Manizales están disponibles las propiedades?",
        "ground_truth": (
            "Inmobiliaria RAG Manizales tiene propiedades disponibles en barrios como El Cable, "
            "La Enea, Chipre, Palermo, Palogrande, Los Agustinos y zonas residenciales del "
            "centro de Manizales."
        ),
    },
    # --- Servicios públicos incluidos (2) ---
    {
        "question": "¿Qué servicios públicos están incluidos en el arriendo?",
        "ground_truth": (
            "Generalmente el valor del arriendo no incluye servicios públicos. Los servicios "
            "de agua, energía eléctrica, gas natural y recolección de basuras son "
            "responsabilidad del arrendatario. En algunos casos, la cuota de administración "
            "del conjunto puede estar incluida."
        ),
    },
    {
        "question": "¿Quién paga los servicios públicos, el arrendador o el arrendatario?",
        "ground_truth": (
            "En los contratos estándar de arrendamiento en Colombia, el arrendatario es "
            "responsable del pago de los servicios públicos domiciliarios (agua, luz, gas). "
            "El arrendador conserva la responsabilidad de servicios comunes del conjunto "
            "residencial."
        ),
    },
    # --- Restricciones de subarriendo (2) ---
    {
        "question": "¿Hay restricciones para subarrendar el apartamento?",
        "ground_truth": (
            "Sí. En la mayoría de los contratos de arrendamiento en Colombia está prohibido "
            "subarrendar el inmueble sin autorización escrita del arrendador. El "
            "incumplimiento de esta cláusula puede ser causal de terminación del contrato."
        ),
    },
    {
        "question": "¿Se puede subarrendar parte del inmueble?",
        "ground_truth": (
            "El subarriendo parcial o total del inmueble requiere autorización expresa y "
            "escrita del arrendador. Esta restricción está contemplada en la Ley 820 de 2003 "
            "que regula el arrendamiento de vivienda urbana en Colombia."
        ),
    },
    # --- Condiciones de pago del canon (1) ---
    {
        "question": "¿Qué condiciones tiene el pago del canon de arrendamiento?",
        "ground_truth": (
            "El canon se paga mensualmente por anticipado dentro de los primeros cinco días "
            "calendario de cada mes. El retraso en el pago genera intereses de mora y puede "
            "ser causal de terminación del contrato. El arrendador puede solicitar paz y "
            "salvo de servicios públicos al momento de la entrega."
        ),
    },
    # --- Descripción de cocinas/amenidades (2) ---
    {
        "question": "¿Cómo es la cocina del apartamento?",
        "ground_truth": (
            "Las cocinas de los apartamentos en el portafolio de Inmobiliaria RAG Manizales "
            "son generalmente integrales o semi-integrales, equipadas con mesón en granito o "
            "cuarzo, gabinetes en madera o melamínico, y conexiones para electrodomésticos. "
            "Algunas propiedades incluyen estufa de gas y horno."
        ),
    },
    {
        "question": "¿El apartamento tiene parqueadero y cuarto útil?",
        "ground_truth": (
            "La disponibilidad de parqueadero y cuarto útil varía según la propiedad. "
            "Muchos apartamentos en Manizales incluyen un puesto de parqueadero cubierto y "
            "un depósito o cuarto útil adicional. Este detalle está especificado en cada "
            "anuncio de la propiedad."
        ),
    },
    # --- Opiniones de usuarios (1) ---
    {
        "question": "¿Qué opinan otros usuarios sobre la propiedad?",
        "ground_truth": (
            "Las opiniones de usuarios sobre propiedades en Inmobiliaria RAG Manizales se "
            "pueden consultar en la plataforma. Los usuarios valoran aspectos como la "
            "ubicación, la atención del arrendador, el estado del inmueble y la relación "
            "precio-calidad del arriendo."
        ),
    },
    # --- Reglamentos de copropiedad (1) ---
    {
        "question": "¿Cuáles son las normas del reglamento de copropiedad?",
        "ground_truth": (
            "El reglamento de copropiedad establece normas sobre uso de zonas comunes, "
            "horarios permitidos para mudanza, prohibición de actividades comerciales en "
            "unidades residenciales, reglas de convivencia, manejo de mascotas y "
            "procedimientos para realizar reformas internas al inmueble."
        ),
    },
    # --- Proceso de arrendamiento (2) ---
    {
        "question": "¿Cuál es el proceso para arrendar una propiedad?",
        "ground_truth": (
            "El proceso de arrendamiento incluye: selección del inmueble, visita presencial, "
            "presentación de documentos (cédula, referencias, certificado laboral, extractos "
            "bancarios), estudio de crédito, firma del contrato y pago del depósito "
            "equivalente a 1 o 2 meses de canon."
        ),
    },
    {
        "question": "¿Qué documentos se necesitan para arrendar un apartamento?",
        "ground_truth": (
            "Para arrendar un apartamento en Inmobiliaria RAG Manizales se requiere: "
            "fotocopia de cédula de ciudadanía, carta laboral o certificado de ingresos, "
            "extractos bancarios de los últimos 3 meses, referencias personales y "
            "comerciales, y en algunos casos la firma de un codeudor."
        ),
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(value, default: float = 0.0) -> float:
    """Converts a value to float safely, returning default on None/NaN."""
    if value is None:
        return default
    try:
        f = float(value)
        return default if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return default


def _ragas_version() -> str:
    try:
        import ragas
        return getattr(ragas, "__version__", "0.2.x")
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# LLM call (standalone — no FastAPI / HTTPException dependencies)
# ---------------------------------------------------------------------------

def call_llm_for_eval(question: str, contexts: List[str]) -> str:
    """Generates a RAG answer using Groq given a question and a list of context chunks."""
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY no configurada en el archivo .env")

    groq_client = Groq(api_key=settings.groq_api_key)

    context_text = "\n\n---\n\n".join(
        f"[Documento {i + 1}]\n{ctx}" for i, ctx in enumerate(contexts)
    )
    user_message = (
        f"Contexto de documentos inmobiliarios:\n\n{context_text}\n\n---\n\n"
        f"Pregunta del usuario: {question}\n\n"
        "Responde basándote exclusivamente en el contexto anterior."
    )

    response = groq_client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
        max_tokens=512,
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# RAGAS metrics builder — RAGAS 0.4.x API
# Usa llm_factory() con el endpoint OpenAI-compatible de Groq (InstructorLLM)
# ---------------------------------------------------------------------------

def build_ragas_metrics():
    """
    Configura las métricas RAGAS 0.4.x usando AsyncOpenAI.

    RAGAS 0.4.x collections metrics requieren un cliente async para ascore().
    Usamos el endpoint OpenAI-compatible de Groq con AsyncOpenAI.

    Returns (metrics_list, evaluator_llm, evaluator_embeddings).
    """
    try:
        from openai import AsyncOpenAI
        from ragas.llms import llm_factory
        from ragas.metrics.collections import Faithfulness, AnswerRelevancy, ContextRecall
        from ragas.embeddings import HuggingFaceEmbeddings as _RagasHFEmb
    except ImportError as exc:
        raise ImportError(
            f"Dependencias de RAGAS no encontradas: {exc}\n"
            "Instala con: pip install ragas>=0.4.0 openai"
        ) from exc

    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY no configurada en .env")

    # AsyncOpenAI es requerido por ascore() — el cliente síncrono no funciona
    groq_async_client = AsyncOpenAI(
        api_key=settings.groq_api_key,
        base_url="https://api.groq.com/openai/v1",
    )
    evaluator_llm = llm_factory(model=settings.groq_model, client=groq_async_client)
    evaluator_embeddings = _RagasHFEmb(model="all-MiniLM-L6-v2")

    metrics = [
        Faithfulness(llm=evaluator_llm),
        AnswerRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings),
        ContextRecall(llm=evaluator_llm),
    ]
    print(f"  [RAGAS] LLM juez    : {settings.groq_model} (vía Groq OpenAI-compatible async)")
    print(f"  [RAGAS] Embeddings  : all-MiniLM-L6-v2 (sentence-transformers, local)")
    return metrics, evaluator_llm, evaluator_embeddings


# ---------------------------------------------------------------------------
# Step 1 — Build evaluation records (RAG pipeline for each question)
# ---------------------------------------------------------------------------

def build_eval_records(
    db,
    strategy: str,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Runs the full RAG pipeline for every ground-truth question under a given
    chunking strategy.  Returns a list of dicts ready for RAGAS evaluation.
    """
    records: List[Dict[str, Any]] = []
    print(f"\n  [{strategy}] Generando respuestas para {len(GROUND_TRUTH)} preguntas...")

    for i, item in enumerate(GROUND_TRUTH, 1):
        question = item["question"]
        ground_truth = item["ground_truth"]

        # 1a. Retrieve relevant chunks via vector search
        raw = vector_search(db, question, strategy=strategy, top_k=top_k)
        contexts = [c["texto"] for c in raw] if raw else []

        if not contexts:
            print(f"    [{i:02d}] SKIP — sin chunks para: {question[:55]}")
            continue

        # 1b. Generate LLM answer
        try:
            answer = call_llm_for_eval(question, contexts)
        except Exception as exc:
            print(f"    [{i:02d}] ERROR LLM — {exc}")
            answer = "No se pudo generar respuesta debido a un error en el LLM."

        records.append(
            {
                "question": question,
                "answer": answer,
                "contexts": contexts,
                "ground_truth": ground_truth,
            }
        )
        print(f"    [{i:02d}] OK — {question[:55]}")

    return records


# ---------------------------------------------------------------------------
# Step 2 — Score each sample via ascore() (bypasses broken evaluate() in 0.4.x)
# ---------------------------------------------------------------------------

async def _score_samples_async(
    records: List[Dict[str, Any]],
    faith: Any,
    ar: Any,
    cr: Any,
) -> List[Dict[str, float]]:
    """Evalúa cada muestra de forma secuencial para respetar los rate limits de Groq."""
    results: List[Dict[str, float]] = []
    n = len(records)
    for i, r in enumerate(records, 1):
        q   = r["question"]
        ans = r["answer"]
        ctx = r["contexts"]
        ref = r["ground_truth"]
        try:
            r_f  = await faith.ascore(user_input=q, response=ans, retrieved_contexts=ctx)
            r_ar = await ar.ascore(user_input=q, response=ans)
            r_cr = await cr.ascore(user_input=q, retrieved_contexts=ctx, reference=ref)
            sample = {
                "faithfulness":     _safe_float(r_f.value  if r_f  else None),
                "answer_relevancy": _safe_float(r_ar.value if r_ar else None),
                "context_recall":   _safe_float(r_cr.value if r_cr else None),
            }
            results.append(sample)
            print(
                f"    [{i:02d}/{n}] RAGAS OK — "
                f"f={sample['faithfulness']:.2f}  "
                f"ar={sample['answer_relevancy']:.2f}  "
                f"cr={sample['context_recall']:.2f}"
            )
        except Exception as exc:
            print(f"    [{i:02d}/{n}] RAGAS ERROR — {exc}")
            results.append({"faithfulness": 0.0, "answer_relevancy": 0.0, "context_recall": 0.0})
    return results


def run_ragas_for_records(
    records: List[Dict[str, Any]],
    metrics: list,
) -> List[Dict[str, float]]:
    """
    Evalúa todos los registros llamando ascore() directamente en cada métrica.

    Bypasses ragas.evaluate() que en RAGAS 0.4.x rechaza las collections metrics
    porque no heredan de ragas.metrics.base.Metric.

    Signatures de ascore() en RAGAS 0.4.x:
      Faithfulness    : (user_input, response, retrieved_contexts) -> MetricResult
      AnswerRelevancy : (user_input, response)                     -> MetricResult
      ContextRecall   : (user_input, retrieved_contexts, reference) -> MetricResult

    Returns List[Dict[str, float]] directamente (sin extract_scores()).
    """
    faith = next((m for m in metrics if m.__class__.__name__ == "Faithfulness"), None)
    ar    = next((m for m in metrics if m.__class__.__name__ == "AnswerRelevancy"), None)
    cr    = next((m for m in metrics if m.__class__.__name__ == "ContextRecall"), None)

    if not all([faith, ar, cr]):
        raise ValueError("Se requieren las tres métricas: Faithfulness, AnswerRelevancy, ContextRecall")

    return asyncio.run(_score_samples_async(records, faith, ar, cr))


# ---------------------------------------------------------------------------
# Step 4 — Persist results to MongoDB (rag_evaluations)
# ---------------------------------------------------------------------------

def save_to_mongodb(
    db,
    records: List[Dict[str, Any]],
    scores: List[Dict[str, float]],
    strategy: str,
) -> int:
    """
    Upserts one document per sample into rag_evaluations.
    Returns the number of documents saved/updated.
    """
    eval_col = db["rag_evaluations"]
    saved = 0
    now = datetime.now(timezone.utc).isoformat()
    ragas_ver = _ragas_version()

    for record, sample_scores in zip(records, scores):
        q_hash = hashlib.md5(
            f"{record['question']}_{strategy}".encode()
        ).hexdigest()[:12]
        doc_id = f"ragas_{strategy[:3]}_{q_hash}"

        doc = {
            "_id": doc_id,
            "id_consulta": doc_id,
            "rag_query_id": doc_id,
            "question": record["question"],
            # RAGAS real metrics
            "faithfulness": sample_scores["faithfulness"],
            "answer_relevancy": sample_scores["answer_relevancy"],
            "context_recall": sample_scores["context_recall"],
            # Compatibility with legacy evaluation fields expected by the frontend
            "relevancia": sample_scores["answer_relevancy"],
            "precision": sample_scores["faithfulness"],
            # Metadata
            "modelo_eval": f"ragas-{ragas_ver}",
            "modelo_llm": settings.groq_model,
            "estrategia_chunking": strategy,
            "respuesta_generada": record["answer"],
            "ground_truth": record["ground_truth"],
            "fecha": now,
        }

        eval_col.update_one({"_id": doc_id}, {"$set": doc}, upsert=True)
        saved += 1

    return saved


# ---------------------------------------------------------------------------
# Main importable function — used by both CLI and API endpoint
# ---------------------------------------------------------------------------

def run_ragas_evaluation(
    strategies: Optional[List[str]] = None,
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    Full RAGAS evaluation pipeline.

    Args:
        strategies: list of chunking strategies to evaluate.
                    Defaults to all three: fixed_size, sentence, semantic.
        top_k:      number of chunks to retrieve per question.

    Returns:
        Dict mapping each strategy name to its average metric scores.
    """
    if strategies is None:
        strategies = ["fixed_size", "sentence", "semantic"]

    db = get_db()
    metrics, _llm, _emb = build_ragas_metrics()

    summary: Dict[str, Any] = {}

    for strategy in strategies:
        print(f"\n{'=' * 60}")
        print(f"  ESTRATEGIA: {strategy.upper()}")
        print(f"{'=' * 60}")

        records = build_eval_records(db, strategy=strategy, top_k=top_k)

        if not records:
            print(f"  [WARNING] Sin registros para '{strategy}' — ¿chunking ejecutado?")
            summary[strategy] = {"error": "Sin chunks disponibles para esta estrategia"}
            continue

        print(f"\n  Ejecutando evaluación RAGAS ({len(records)} registros)...")
        scores = run_ragas_for_records(records, metrics)
        saved = save_to_mongodb(db, records, scores, strategy)
        print(f"  Guardados {saved} documentos en rag_evaluations.")

        # Compute averages
        avg_faith = sum(s["faithfulness"] for s in scores) / len(scores)
        avg_ar = sum(s["answer_relevancy"] for s in scores) / len(scores)
        avg_cr = sum(s["context_recall"] for s in scores) / len(scores)

        summary[strategy] = {
            "faithfulness": round(avg_faith, 4),
            "answer_relevancy": round(avg_ar, 4),
            "context_recall": round(avg_cr, 4),
            "n_samples": len(records),
        }

        print(f"\n  Faithfulness promedio:      {avg_faith:.4f}")
        print(f"  Answer Relevancy promedio:  {avg_ar:.4f}")
        print(f"  Context Recall promedio:    {avg_cr:.4f}")

    return summary


# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------

def print_summary(summary: Dict[str, Any]) -> None:
    print("\n" + "=" * 50)
    print("  RESULTADOS EVALUACIÓN RAGAS")
    print("=" * 50)

    best_strategy: Optional[str] = None
    best_faith = -1.0

    for strategy, data in summary.items():
        if "error" in data:
            print(f"\nEstrategia: {strategy}")
            print(f"  ERROR: {data['error']}")
            continue

        print(f"\nEstrategia: {strategy}")
        print(f"  Faithfulness promedio:     {data['faithfulness']:.4f}")
        print(f"  Answer Relevancy promedio: {data['answer_relevancy']:.4f}")
        print(f"  Context Recall promedio:   {data['context_recall']:.4f}")
        print(f"  Muestras evaluadas:        {data['n_samples']}")

        if data["faithfulness"] > best_faith:
            best_faith = data["faithfulness"]
            best_strategy = strategy

    print("\n" + "-" * 50)
    if best_strategy:
        print(f"  Mejor estrategia: {best_strategy}  (faithfulness: {best_faith:.4f})")
    print("=" * 50)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluación RAGAS del sistema RAG Inmobiliaria Manizales"
    )
    parser.add_argument(
        "--strategy",
        choices=["all", "fixed_size", "sentence", "semantic"],
        default="all",
        help="Estrategia de chunking a evaluar (default: all)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        metavar="K",
        help="Número de chunks a recuperar por consulta (default: 5)",
    )
    args = parser.parse_args()

    strategies = (
        ["fixed_size", "sentence", "semantic"]
        if args.strategy == "all"
        else [args.strategy]
    )

    print("=" * 60)
    print("  EVALUACIÓN RAGAS — RAG Inmobiliaria Manizales")
    print(f"  Estrategias : {', '.join(strategies)}")
    print(f"  Top-K chunks: {args.top_k}")
    print(f"  Preguntas GT: {len(GROUND_TRUTH)}")
    print(f"  Versión RAGAS: {_ragas_version()}")
    print("=" * 60)

    try:
        summary = run_ragas_evaluation(strategies=strategies, top_k=args.top_k)
        print_summary(summary)
    finally:
        close()


if __name__ == "__main__":
    main()
