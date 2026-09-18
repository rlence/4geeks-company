"""Mide Recall@3 del retrieval contra data/eval/test-queries.json (Hito 7).

Recall@3 = porcentaje de preguntas cuyo chunk esperado aparece entre los 3
primeros resultados de retrieve(). El CONTEXT §4 exige ≥ 80%.

Es también la herramienta con la que se afina MIN_SCORE: se puede pasar un
umbral distinto para comparar sin tocar el código del pipeline.

    # umbral actual del pipeline
    uv run --project services/api python data/eval/recall_at_3.py

    # barrido para elegir umbral
    uv run --project services/api python data/eval/recall_at_3.py --sweep

Requiere Qdrant arriba y la colección ya indexada (data/process/rag_index.py).
"""

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "data" / "process"))
sys.path.insert(0, str(_ROOT / "data" / "pipelines"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_ROOT / ".env")

import rag  # noqa: E402

QUERIES_PATH = _ROOT / "data" / "eval" / "test-queries.json"
K = 3


def _load_queries() -> tuple[list[dict], float]:
    data = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))
    return data["queries"], data.get("recall_at_3_threshold", 0.8)


def _rank_of_expected(results: list[dict], expected_doc: str, expected_index: int) -> int | None:
    """Posición (1-based) del chunk esperado entre los resultados, o None."""
    for position, payload in enumerate(results, start=1):
        if (
            payload.get("source_document") == expected_doc
            and payload.get("chunk_index") == expected_index
        ):
            return position
    return None


def evaluate(min_score: float, *, verbose: bool = True) -> float:
    queries, _ = _load_queries()
    hits = 0

    for entry in queries:
        results = rag.retrieve(entry["question"], k=K, min_score=min_score)
        rank = _rank_of_expected(
            results, entry["expected_source_document"], entry["expected_chunk_index"]
        )
        if rank is not None:
            hits += 1

        if verbose:
            mark = "✓" if rank else "✗"
            found = f"pos {rank}" if rank else f"NO en top-{K}"
            recuperados = ", ".join(
                f"{p.get('source_document')}#{p.get('chunk_index')}" for p in results
            ) or "(nada sobre el umbral)"
            print(f"  {mark} {found:12s} {entry['question'][:58]}")
            print(f"      esperado: {entry['expected_source_document']}#{entry['expected_chunk_index']}")
            print(f"      top-{K}:    {recuperados}")

    return hits / len(queries) if queries else 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-score", type=float, default=rag.MIN_SCORE)
    parser.add_argument(
        "--sweep", action="store_true", help="prueba varios umbrales para afinar MIN_SCORE"
    )
    args = parser.parse_args()

    _, threshold = _load_queries()

    if args.sweep:
        print("Barrido de umbrales (Recall@3):\n")
        for candidate in (0.0, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6):
            recall = evaluate(candidate, verbose=False)
            flag = "OK " if recall >= threshold else "   "
            print(f"  {flag} min_score={candidate:.2f} -> Recall@3 = {recall:.0%}")
        return 0

    print(f"Recall@{K} con min_score={args.min_score:.2f}\n")
    recall = evaluate(args.min_score)
    print(f"\nRecall@{K} = {recall:.0%} (umbral del CONTEXT: {threshold:.0%})")

    if recall < threshold:
        print("FALLA: por debajo del umbral del CONTEXT.")
        return 1
    print("OK: cumple el umbral del CONTEXT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
