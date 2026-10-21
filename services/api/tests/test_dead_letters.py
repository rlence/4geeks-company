"""La DLQ conserva una referencia mínima y una auditoría separada."""

from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import dead_letters


class Table:
    def __init__(self):
        self.saved = None
        self.updated = None
        self.filtered = None

    def upsert(self, payload, **kwargs):
        self.saved = payload
        return self

    def update(self, payload):
        self.updated = payload
        return self

    def eq(self, column, value):
        self.filtered = (column, value)
        return self

    def execute(self):
        return SimpleNamespace(data=[])


class Client:
    def __init__(self):
        self.data = Table()

    def table(self, name):
        assert name == "task_dead_letters"
        return self.data


def test_terminal_failure_persists_then_publishes_minimal_message(monkeypatch):
    task_id = str(uuid4())
    client = Client()
    calls = []
    monkeypatch.setattr(dead_letters, "get_client", lambda: client)
    monkeypatch.setattr(dead_letters.app, "send_task", lambda name, **kw: calls.append((name, kw)))
    dead_letters.record_terminal_failure(task_id, date(2026, 9, 7), 4, RuntimeError("broken"))
    assert client.data.saved["task_id"] == task_id
    assert client.data.saved["attempt_count"] == 4
    assert client.data.updated["publish_status"] == "published"
    assert client.data.updated["published_at"]
    assert calls[0][0] == "reporting.dead_letter"
    assert calls[0][1]["args"] == [task_id]
    assert calls[0][1]["queue"] == "dead_letter"


def test_publish_failure_leaves_db_row_pending(monkeypatch):
    task_id = str(uuid4())
    client = Client()
    monkeypatch.setattr(dead_letters, "get_client", lambda: client)
    def fail(*_args, **_kwargs):
        raise ConnectionError("broker offline")
    monkeypatch.setattr(dead_letters.app, "send_task", fail)
    try:
        dead_letters.record_terminal_failure(task_id, date(2026, 9, 7), 4, RuntimeError("broken"))
    except ConnectionError:
        pass
    else:
        raise AssertionError("publication should fail")
    assert client.data.saved["publish_status"] == "pending"
    assert client.data.updated is None
