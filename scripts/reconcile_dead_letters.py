"""Republica entradas DLQ que quedaron pendientes tras un fallo de Redis."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "api"))

from dead_letters import TABLE, get_client, publish_dead_letter  # noqa: E402


def main() -> int:
    client = get_client()
    rows = (
        client.table(TABLE).select("task_id")
        .eq("publish_status", "pending")
        .order("failed_at").limit(100).execute().data
    )
    for row in rows:
        publish_dead_letter(row["task_id"], client)
    print(f"Published {len(rows)} pending dead letters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
