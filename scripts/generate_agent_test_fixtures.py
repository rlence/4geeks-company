"""Genera artefactos CI con el grafo real y proveedores simulados explícitos.

No son evidencia de calidad del modelo ni de recuperación real.
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))
from capture_agent_traces import CASES
from support_agent.graph import rag
from support_agent.service import AgentError, open_service
import rag_index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    documents = {d["source_document"]: rag_index.chunk_document(d["text"], d["source_document"])
                 for d in rag_index.load_documents()}

    def retrieve(question):
        if "Oro" in question:
            return documents["loyalty-program"]
        if "maní" in question:
            return documents["menu-allergens"]
        return []

    def generate(question, context):
        if not context:
            return "No tengo información sobre ese horario en la base de conocimiento."
        if "Oro" in question:
            return "Necesitas 50 puntos o más para Oro, con 15% de descuento permanente."
        return "La Costilla BBQ puede contener trazas de maní. Nunca se garantiza cero riesgo de contaminación cruzada."

    manifest = {"mode": "mock", "cases": {}}
    with tempfile.TemporaryDirectory() as runtime, patch.object(rag, "retrieve", retrieve), patch.object(rag, "generate_answer", generate):
        with open_service(runtime, args.output_dir, mode="mock") as service:
            for case, question in CASES.items():
                try:
                    _, run_id = service.query(question)
                except AgentError as exc:
                    if exc.code != "invalid_question":
                        raise
                    run_id = exc.run_id
                manifest["cases"][case] = f"{run_id}.json"
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Generadas 4 trazas MOCK para CI; no equivalen a corridas reales.")


if __name__ == "__main__":
    main()
