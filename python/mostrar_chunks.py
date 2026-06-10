"""
Muestra los chunks recuperados para una consulta en las 3 estrategias.

Uso:
    python mostrar_chunks.py
    python mostrar_chunks.py "¿Cuánto cuesta el arriendo?"
    python mostrar_chunks.py "¿Se permiten mascotas?" --top-k 5 --full
"""
import sys
import io
import argparse

# Forzar UTF-8 en Windows para evitar UnicodeEncodeError
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, ".")
from database import get_db, close
from chunking_pipeline import vector_search

QUERIES_DEMO = [
    "¿Se permiten mascotas en el apartamento?",
    "¿Cuál es el valor del arriendo mensual?",
    "¿Qué incluye el contrato de arrendamiento?",
    "¿Cuántas habitaciones tiene la propiedad?",
    "¿Qué servicios públicos están incluidos?",
]

STRATEGIES = ["fixed_size", "sentence", "semantic"]

STRATEGY_LABELS = {
    "fixed_size": "FIXED SIZE  (tamaño fijo, 1024 chars)",
    "sentence":   "SENTENCE    (por oraciones, hasta 5 oraciones)",
    "semantic":   "SEMANTIC    (por similitud semántica, umbral 0.80)",
}


def score_bar(score: float, width: int = 20) -> str:
    filled = int(round(score * width))
    return "█" * filled + "░" * (width - filled)


def run(query: str, top_k: int, full: bool) -> None:
    db = get_db()

    print()
    print("=" * 70)
    print(f"  CONSULTA: {query}")
    print(f"  Top-K   : {top_k} chunks por estrategia")
    print("=" * 70)

    all_results = {}
    for strategy in STRATEGIES:
        results = vector_search(db, query, strategy=strategy, top_k=top_k)
        all_results[strategy] = results

    # ---- Tabla resumen de scores ----
    print()
    print(f"  {'Estrategia':<14} {'Chunks en DB':>12}  Scores recuperados")
    print("  " + "-" * 60)
    for strategy in STRATEGIES:
        results = all_results[strategy]
        scores = [r["score"] for r in results]
        avg = sum(scores) / len(scores) if scores else 0
        from database import get_db as _get
        total = db["document_chunks"].count_documents({"estrategia_chunking": strategy})
        bar = score_bar(avg)
        print(f"  {strategy:<14} {total:>12}  {bar}  avg={avg:.4f}")

    # ---- Detalle por estrategia ----
    for strategy in STRATEGIES:
        results = all_results[strategy]
        print()
        print("─" * 70)
        print(f"  {STRATEGY_LABELS[strategy]}")
        print("─" * 70)

        if not results:
            print("  (sin resultados — ¿ejecutaste chunking_pipeline.py?)")
            continue

        for i, r in enumerate(results, 1):
            score = r.get("score", 0.0)
            texto = r.get("texto", "")
            doc_id = r.get("doc_id", "?")
            chunk_idx = r.get("chunk_index", "?")

            # score con barra visual
            bar = score_bar(score, 15)
            nivel = "ALTO" if score >= 0.82 else ("MEDIO" if score >= 0.70 else "BAJO")

            print(f"\n  [{i}] Score: {score:.4f}  {bar}  [{nivel}]")
            print(f"       Doc: {doc_id}  |  Chunk #{chunk_idx}")

            if full:
                # Texto completo con indentación
                lineas = [texto[j:j+65] for j in range(0, len(texto), 65)]
                for linea in lineas:
                    print(f"       {linea}")
            else:
                # Solo los primeros 200 chars
                preview = texto[:200].replace("\n", " ")
                if len(texto) > 200:
                    preview += "..."
                print(f"       {preview}")

    print()
    print("=" * 70)
    print("  CONCLUSIÓN PARA ESTA CONSULTA:")

    # La estrategia ganadora
    avgs = {
        s: sum(r["score"] for r in all_results[s]) / len(all_results[s])
        for s in STRATEGIES if all_results[s]
    }
    if avgs:
        winner = max(avgs, key=avgs.get)
        print(f"  Mejor estrategia: {winner.upper()}  (score promedio: {avgs[winner]:.4f})")
        for s in STRATEGIES:
            if s in avgs:
                mark = "  ◄ MEJOR" if s == winner else ""
                print(f"    {s:<14}: {avgs[s]:.4f}{mark}")
    print("=" * 70)
    print()

    close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Muestra chunks recuperados para una consulta en las 3 estrategias"
    )
    parser.add_argument(
        "query",
        nargs="?",
        default=None,
        help="Consulta a buscar (default: menú interactivo)",
    )
    parser.add_argument(
        "--top-k", type=int, default=3, metavar="K",
        help="Número de chunks a recuperar por estrategia (default: 3)",
    )
    parser.add_argument(
        "--full", action="store_true",
        help="Mostrar texto completo de cada chunk (default: solo preview)",
    )
    args = parser.parse_args()

    if args.query:
        run(args.query, args.top_k, args.full)
    else:
        # Menú interactivo
        print()
        print("=" * 70)
        print("  VISUALIZADOR DE CHUNKS — RAG Inmobiliaria Manizales")
        print("=" * 70)
        print()
        print("  Consultas de ejemplo:")
        for i, q in enumerate(QUERIES_DEMO, 1):
            print(f"    [{i}] {q}")
        print(f"    [{len(QUERIES_DEMO)+1}] Escribir consulta personalizada")
        print()

        try:
            opcion = input("  Selecciona una opción (1-6): ").strip()
            if opcion.isdigit() and 1 <= int(opcion) <= len(QUERIES_DEMO):
                query = QUERIES_DEMO[int(opcion) - 1]
            else:
                query = input("  Escribe tu consulta: ").strip()
                if not query:
                    print("  Consulta vacía, usando la primera de la lista.")
                    query = QUERIES_DEMO[0]

            top_k_input = input(f"  Top-K chunks (Enter para 3): ").strip()
            top_k = int(top_k_input) if top_k_input.isdigit() else 3

            full_input = input("  ¿Mostrar texto completo? (s/N): ").strip().lower()
            full = full_input in ("s", "si", "sí", "y", "yes")

        except (KeyboardInterrupt, EOFError):
            print("\n  Cancelado.")
            return

        run(query, top_k, full)


if __name__ == "__main__":
    main()
