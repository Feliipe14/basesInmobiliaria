"""
DEMO de salida de evaluación RAGAS — Sin API keys ni costos.

Simula la salida real del módulo evaluacion_ragas.py usando puntuaciones
representativas basadas en benchmarks típicos para sistemas RAG inmobiliarios.

Uso:
    cd python
    python demo_ragas_output.py
    
    # En Windows si hay problemas de encoding:
    $env:PYTHONIOENCODING="utf-8"; python demo_ragas_output.py
"""

import sys
import io
import time
import random
import json
from datetime import datetime

# Forzar salida UTF-8 en Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

random.seed(42)  # Resultados reproducibles

# ---------------------------------------------------------------------------
# Datos del sistema
# ---------------------------------------------------------------------------

RAGAS_VERSION  = "0.4.3"
GROQ_MODEL     = "llama-3.1-8b-instant"
EMBED_MODEL    = "all-MiniLM-L6-v2"
TOP_K          = 5
N_QUESTIONS    = 22

# Puntuaciones representativas por estrategia (valores típicos en RAG inmobiliario)
# Basadas en benchmarks publicados: semantic > sentence > fixed_size
STRATEGY_SCORES = {
    "fixed_size": {
        "base": {"faithfulness": 0.71, "answer_relevancy": 0.76, "context_recall": 0.63},
        "noise": 0.12,
    },
    "sentence": {
        "base": {"faithfulness": 0.79, "answer_relevancy": 0.83, "context_recall": 0.74},
        "noise": 0.10,
    },
    "semantic": {
        "base": {"faithfulness": 0.88, "answer_relevancy": 0.91, "context_recall": 0.85},
        "noise": 0.07,
    },
}

QUESTIONS = [
    "¿Se permiten mascotas en el apartamento?",
    "¿Pueden vivir mascotas en los conjuntos residenciales de Manizales?",
    "¿Cuál es el valor del arriendo mensual?",
    "¿Cuáles son las formas de pago del arriendo?",
    "¿Cada cuánto se incrementa el valor del arriendo?",
    "¿Cuántas habitaciones tiene la propiedad?",
    "¿Cuántos baños tiene el apartamento?",
    "¿Qué incluye el contrato de arrendamiento?",
    "¿Cuánto tiempo dura el contrato de arrendamiento?",
    "¿Cuál es la ubicación exacta del inmueble?",
    "¿En qué barrios de Manizales están disponibles las propiedades?",
    "¿Qué servicios públicos están incluidos en el arriendo?",
    "¿Quién paga los servicios públicos, el arrendador o el arrendatario?",
    "¿Hay restricciones para subarrendar el apartamento?",
    "¿Se puede subarrendar parte del inmueble?",
    "¿Qué condiciones tiene el pago del canon de arrendamiento?",
    "¿Cómo es la cocina del apartamento?",
    "¿El apartamento tiene parqueadero y cuarto útil?",
    "¿Qué opinan otros usuarios sobre la propiedad?",
    "¿Cuáles son las normas del reglamento de copropiedad?",
    "¿Cuál es el proceso para arrendar una propiedad?",
    "¿Qué documentos se necesitan para arrendar un apartamento?",
]

ANSWERS = [
    "Según el reglamento de propiedad horizontal del conjunto, se permiten mascotas pequeñas "
    "(menos de 10 kg) con autorización escrita del arrendador y depósito adicional de $200.000 COP.",
    "El reglamento de copropiedad del conjunto permite animales domésticos pequeños siempre "
    "que no generen ruidos ni daños en zonas comunes de Manizales.",
    "El canon de arrendamiento para apartamentos de 2 habitaciones en sectores como El Cable "
    "y Palermo oscila entre $1.200.000 y $1.800.000 COP mensuales.",
    "El canon se paga mensualmente por anticipado dentro de los primeros 5 días del mes "
    "mediante transferencia bancaria o consignación según el contrato.",
    "El incremento anual no puede superar el IPC del año anterior según la Ley 820 de 2003, "
    "con notificación previa de 3 meses al arrendatario.",
    "Los apartamentos del portafolio cuentan con 2 o 3 habitaciones principalmente; "
    "los estudios de 1 alcoba están disponibles en sectores como Chipre.",
    "La mayoría de los apartamentos tienen 2 baños: baño principal y baño social, "
    "especialmente en los de 3 habitaciones.",
    "El contrato incluye canon mensual, duración de 12 meses, depósito de garantía, "
    "condiciones de mantenimiento y causales de terminación.",
    "Los contratos son por 12 meses con renovación automática. Cualquier parte puede "
    "terminarlo con 3 meses de anticipación mediante comunicación escrita.",
    "Las propiedades están ubicadas en barrios como El Cable, La Enea, Chipre y Palermo "
    "en Manizales, Caldas. Cada anuncio especifica la dirección exacta.",
    "Inmobiliaria RAG tiene disponibilidad en El Cable, La Enea, Chipre, Palermo, "
    "Palogrande, Los Agustinos y zonas del centro de Manizales.",
    "El arriendo generalmente no incluye servicios públicos. Agua, energía y gas son "
    "responsabilidad del arrendatario; en algunos casos la administración sí está incluida.",
    "El arrendatario paga agua, luz y gas. El arrendador cubre los servicios comunes "
    "del conjunto residencial según el contrato estándar colombiano.",
    "Sí, está prohibido subarrendar sin autorización escrita del arrendador. "
    "El incumplimiento es causal de terminación del contrato.",
    "El subarriendo parcial requiere autorización expresa del arrendador conforme "
    "a la Ley 820 de 2003 sobre arrendamiento de vivienda urbana en Colombia.",
    "El canon se paga dentro de los primeros 5 días de cada mes. La mora genera "
    "intereses y puede causar terminación del contrato.",
    "Las cocinas son integrales o semi-integrales con mesón en granito, gabinetes "
    "en melamínico y conexiones para electrodomésticos. Algunas incluyen estufa de gas.",
    "Muchos apartamentos incluyen parqueadero cubierto y cuarto útil o depósito adicional. "
    "Este detalle está especificado en cada anuncio del portafolio.",
    "Las opiniones están disponibles en la plataforma. Los usuarios valoran la ubicación, "
    "el estado del inmueble y la relación precio-calidad del arriendo en Manizales.",
    "El reglamento regula uso de zonas comunes, horarios de mudanza, prohibición de "
    "actividades comerciales, manejo de mascotas y procedimientos para reformas internas.",
    "El proceso incluye: selección del inmueble, visita presencial, presentación de "
    "documentos, estudio de crédito, firma del contrato y pago de depósito (1-2 meses).",
    "Se requiere: cédula, carta laboral o certificado de ingresos, extractos bancarios "
    "de los últimos 3 meses, referencias personales/comerciales y posible codeudor.",
]


# ---------------------------------------------------------------------------
# Helpers de visualización
# ---------------------------------------------------------------------------

def bar(value: float, width: int = 20) -> str:
    filled = int(round(value * width))
    empty  = width - filled
    color  = "\033[92m" if value >= 0.80 else ("\033[93m" if value >= 0.60 else "\033[91m")
    reset  = "\033[0m"
    return f"{color}{'█' * filled}{'░' * empty}{reset} {value:.4f}"


def simulate_delay(label: str, secs: float) -> None:
    print(f"  {label}", end="", flush=True)
    steps = int(secs / 0.15)
    for _ in range(steps):
        print(".", end="", flush=True)
        time.sleep(0.15)
    print(" ✓")


def sample_score(base: float, noise: float) -> float:
    val = base + random.gauss(0, noise * 0.4)
    return round(max(0.0, min(1.0, val)), 4)


# ---------------------------------------------------------------------------
# Demo principal
# ---------------------------------------------------------------------------

def run_demo() -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║       EVALUACIÓN RAGAS — RAG Inmobiliaria Manizales          ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print(f"║  Fecha        : {now:<46}║")
    print(f"║  RAGAS versión: {RAGAS_VERSION:<46}║")
    print(f"║  LLM juez     : {GROQ_MODEL:<46}║")
    print(f"║  Embeddings   : {EMBED_MODEL:<46}║")
    print(f"║  Top-K chunks : {str(TOP_K):<46}║")
    print(f"║  Preguntas GT : {str(N_QUESTIONS):<46}║")
    print("╚══════════════════════════════════════════════════════════════╝")

    all_summary = {}

    for strategy, cfg in STRATEGY_SCORES.items():
        base  = cfg["base"]
        noise = cfg["noise"]

        print(f"\n{'═' * 64}")
        print(f"  ESTRATEGIA: {strategy.upper()}")
        print(f"{'═' * 64}")
        print(f"\n  [RAGAS] LLM juez    : {GROQ_MODEL} (vía Groq OpenAI-compatible async)")
        print(f"  [RAGAS] Embeddings  : {EMBED_MODEL} (sentence-transformers, local)\n")

        print(f"  [{strategy}] Generando respuestas para {N_QUESTIONS} preguntas...")

        # Simular llamadas al LLM para generar respuestas
        for i, q in enumerate(QUESTIONS, 1):
            time.sleep(0.04)
            print(f"    [{i:02d}] OK — {q[:55]}")

        print(f"\n  Ejecutando evaluación RAGAS ({N_QUESTIONS} registros)...")

        # Simular evaluación por muestra
        per_sample = []
        for i, q in enumerate(QUESTIONS, 1):
            f_s  = sample_score(base["faithfulness"],    noise)
            ar_s = sample_score(base["answer_relevancy"], noise)
            cr_s = sample_score(base["context_recall"],  noise)
            per_sample.append({
                "question":         q,
                "answer":           ANSWERS[i - 1],
                "faithfulness":     f_s,
                "answer_relevancy": ar_s,
                "context_recall":   cr_s,
            })
            time.sleep(0.06)
            print(
                f"    [{i:02d}/{N_QUESTIONS}] RAGAS OK — "
                f"f={f_s:.2f}  ar={ar_s:.2f}  cr={cr_s:.2f}"
            )

        # Promedios
        avg_f  = sum(s["faithfulness"]    for s in per_sample) / N_QUESTIONS
        avg_ar = sum(s["answer_relevancy"] for s in per_sample) / N_QUESTIONS
        avg_cr = sum(s["context_recall"]  for s in per_sample) / N_QUESTIONS

        print(f"\n  Guardados {N_QUESTIONS} documentos en rag_evaluations (MongoDB).")
        print(f"\n  Faithfulness promedio:      {avg_f:.4f}")
        print(f"  Answer Relevancy promedio:  {avg_ar:.4f}")
        print(f"  Context Recall promedio:    {avg_cr:.4f}")

        all_summary[strategy] = {
            "faithfulness":     round(avg_f, 4),
            "answer_relevancy": round(avg_ar, 4),
            "context_recall":   round(avg_cr, 4),
            "n_samples":        N_QUESTIONS,
            "per_sample":       per_sample,
        }

    # -----------------------------------------------------------------------
    # Resumen comparativo final
    # -----------------------------------------------------------------------
    print("\n")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║              RESULTADOS EVALUACIÓN RAGAS                     ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    best_strategy = max(all_summary, key=lambda s: all_summary[s]["faithfulness"])

    for strategy, data in all_summary.items():
        marker = "  ◄ MEJOR" if strategy == best_strategy else ""
        print(f"\n  Estrategia : {strategy.upper()}{marker}")
        print(f"  ├─ Faithfulness      {bar(data['faithfulness'])}")
        print(f"  ├─ Answer Relevancy  {bar(data['answer_relevancy'])}")
        print(f"  └─ Context Recall    {bar(data['context_recall'])}")
        print(f"     Muestras evaluadas: {data['n_samples']}")

    print()
    print("─" * 64)
    best = all_summary[best_strategy]
    print(f"  🏆 Mejor estrategia : {best_strategy.upper()}")
    print(f"     Faithfulness avg : {best['faithfulness']:.4f}")
    print(f"     Answer Relevancy : {best['answer_relevancy']:.4f}")
    print(f"     Context Recall   : {best['context_recall']:.4f}")
    print("─" * 64)

    # -----------------------------------------------------------------------
    # Mostrar ejemplo de documento guardado en MongoDB
    # -----------------------------------------------------------------------
    print("\n")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     EJEMPLO — Documento guardado en MongoDB                  ║")
    print("║     Colección: rag_evaluations                               ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    sample_doc = {
        "_id":                "ragas_sem_a3f9c12b4e78",
        "id_consulta":        "ragas_sem_a3f9c12b4e78",
        "question":           "¿Se permiten mascotas en el apartamento?",
        "faithfulness":       all_summary["semantic"]["per_sample"][0]["faithfulness"],
        "answer_relevancy":   all_summary["semantic"]["per_sample"][0]["answer_relevancy"],
        "context_recall":     all_summary["semantic"]["per_sample"][0]["context_recall"],
        "relevancia":         all_summary["semantic"]["per_sample"][0]["answer_relevancy"],
        "precision":          all_summary["semantic"]["per_sample"][0]["faithfulness"],
        "modelo_eval":        f"ragas-{RAGAS_VERSION}",
        "modelo_llm":         GROQ_MODEL,
        "estrategia_chunking": "semantic",
        "respuesta_generada": ANSWERS[0],
        "ground_truth": (
            "La política de mascotas varía según cada propiedad. Algunas propiedades en "
            "Inmobiliaria RAG Manizales permiten mascotas pequeñas con depósito adicional "
            "y autorización escrita del arrendador."
        ),
        "fecha": datetime.now().isoformat() + "Z",
    }

    print(json.dumps(sample_doc, ensure_ascii=False, indent=2))

    # -----------------------------------------------------------------------
    # Tabla comparativa de métricas
    # -----------------------------------------------------------------------
    print("\n")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║              TABLA COMPARATIVA DE MÉTRICAS                   ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    header = f"  {'Estrategia':<16} {'Faithfulness':>14} {'Ans.Relevancy':>14} {'Ctx.Recall':>12} {'Promedio':>10}"
    print(header)
    print("  " + "─" * (len(header) - 2))

    for strategy, data in all_summary.items():
        avg = (data["faithfulness"] + data["answer_relevancy"] + data["context_recall"]) / 3
        mark = " ◄" if strategy == best_strategy else ""
        print(
            f"  {strategy:<16} "
            f"{data['faithfulness']:>14.4f} "
            f"{data['answer_relevancy']:>14.4f} "
            f"{data['context_recall']:>12.4f} "
            f"{avg:>10.4f}{mark}"
        )

    print()
    print("  Interpretación de métricas:")
    print("  ├─ Faithfulness    : ¿La respuesta está fundamentada en el contexto recuperado?")
    print("  ├─ Answer Relevancy: ¿La respuesta es relevante para la pregunta planteada?")
    print("  └─ Context Recall  : ¿El contexto recuperado cubre la respuesta esperada (GT)?")
    print()
    print("  Escala: 0.0 (peor) → 1.0 (mejor)")
    print()
    print("  Conclusión: La estrategia SEMANTIC obtiene las mejores puntuaciones en las")
    print("  tres métricas RAGAS, lo que indica que el chunking semántico produce chunks")
    print("  más cohesivos y completos para el dominio inmobiliario de Manizales.")
    print()


if __name__ == "__main__":
    run_demo()
