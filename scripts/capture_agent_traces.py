"""Captura corridas reales; los evals posteriores no llaman a proveedores."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))
from dotenv import load_dotenv
from support_agent.service import AgentError, open_service

CASES = {
    "gold": "¿Cuántos puntos necesito para llegar al nivel Oro?",
    "allergens": "¿La Costilla BBQ es segura para alguien con alergia al maní?",
    "unknown": "¿Cuál es el horario del local de Miami?",
    "empty": "   ",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    load_dotenv(ROOT / ".env")
    missing = [key for key in ("LLM_API_KEY", "EMBEDDING_MODEL", "GENERATION_MODEL")
               if not __import__("os").environ.get(key)]
    if missing:
        print("Falta configuración: " + ", ".join(missing))
        return 1
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"mode": "live", "cases": {}}
    failed = False
    with open_service(trace_dir=args.output_dir) as service:
        for case, question in CASES.items():
            try:
                _, run_id = service.query(question)
                status = "completed"
            except AgentError as exc:
                run_id, status = exc.run_id, exc.code
                failed |= not (case == "empty" and status == "invalid_question")
            manifest["cases"][case] = f"{run_id}.json"
            print(f"{case}: {status} ({run_id})")
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
