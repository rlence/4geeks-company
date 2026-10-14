"""Reject compromised sources before the graph can checkpoint their payloads."""
from .policy import unsafe_reason
from .events import record


def safe_records(records, *, memory=False):
    if not isinstance(records, list):
        record("external", "structural", "block", "invalid_collection")
        return []
    if len(records) > 20:
        record("external", "structural", "block", "collection_limit")
    result = []
    field = "fact" if memory else "text"
    for item in records[:20]:
        if not isinstance(item, dict) or not isinstance(item.get(field), str) or len(item[field]) > 12000:
            record("external", "structural", "block", "invalid_record")
            continue
        allowed = ("fact", "approved_at", "location_id") if memory else ("text", "source_document", "section")
        clean = {key: item[key] for key in allowed if key in item}
        if any(not isinstance(value, (str, int, type(None))) for value in clean.values()):
            record("external", "structural", "block", "invalid_metadata")
            continue
        reason = unsafe_reason(" ".join(str(value) for value in clean.values()))
        if reason:
            record("external", "security" if reason == "instruction_override" else "content", "block", reason)
            continue
        if memory and (not isinstance(clean.get("approved_at"), str) or len(clean["approved_at"]) < 10):
            record("external", "structural", "block", "invalid_memory_date")
            continue
        result.append(clean)
    return result
