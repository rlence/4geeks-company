"""Inspecciona checkpoints persistidos sin ejecutar el grafo ni los proveedores."""
import argparse
import json
import sys
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services/api"))
from support_agent.service import DEFAULT_RUNTIME, open_service


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id", type=UUID)
    parser.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)
    args = parser.parse_args()
    if not (args.runtime_dir / "checkpoints.sqlite").is_file():
        parser.error("No existe la base de checkpoints")
    with open_service(args.runtime_dir) as service:
        history = list(service.graph.get_state_history({"configurable": {"thread_id": str(args.run_id)}}))
        if not history:
            parser.error("No hay checkpoints para esa corrida")
        print(json.dumps([{"checkpoint_id": s.config["configurable"]["checkpoint_id"],
                           "next": s.next, "values": s.values} for s in reversed(history)],
                         ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
