"""Summarize a test session without reading or printing prompt payloads."""
import argparse
from collections import Counter
import json
from pathlib import Path


def summarize(directory):
    counts = Counter()
    runs = set()
    invalid = []
    for path in sorted(Path(directory).glob("*.json")):
        if path.name == "manifest.json":
            continue
        try:
            trace = json.loads(path.read_text())
            run = trace["run_id"]
            if not isinstance(run, str) or trace.get("status") == "running":
                raise ValueError("Incomplete trace")
            events = trace.get("guardrails", [])
            batch = Counter()
            for event in events:
                if event["failure_type"] not in {"structural", "content", "security"} or event["action"] not in {"block", "redirect"}:
                    raise ValueError("Invalid event")
                batch[(event["guardrail_id"], event["failure_type"], event["action"])] += 1
            if run not in runs:
                counts.update(batch)
                runs.add(run)
        except (ValueError, KeyError, TypeError, OSError):
            invalid.append(path.name)
    return {"runs": len(runs), "total": sum(counts.values()),
            "counts": [{"guardrail_id": key[0], "failure_type": key[1], "action": key[2], "count": count}
                       for key, count in sorted(counts.items())], "invalid_files": invalid}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Trace directory for one test session")
    args = parser.parse_args()
    if not args.directory.is_dir():
        parser.error("Trace directory does not exist")
    result = summarize(args.directory)
    print(json.dumps(result, indent=2))
    return 1 if result["invalid_files"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
