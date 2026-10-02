"""Una instancia por proceso; estado por consulta persistido por thread_id."""
import hashlib
import logging
import os
import sqlite3
import subprocess
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from .graph import ROOT, NodeFailure, StateContract, build_graph, rag, next_node
from .traces import Event, Trace, save_trace

logger = logging.getLogger(__name__)
DEFAULT_RUNTIME = Path(__file__).resolve().parents[1] / ".agent-runtime"


class AgentError(RuntimeError):
    def __init__(self, code, run_id):
        self.code, self.run_id = code, run_id
        super().__init__(code)


def provenance(mode="live"):
    def git(*args):
        try:
            result = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            return "unknown"
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    corpus = ROOT / "docs" / "company-knowledge-base"
    paths = [*sorted(corpus.glob("*.md")), *sorted(Path(__file__).parent.rglob("*.py")),
             ROOT / "data/pipelines/rag.py", ROOT / "data/process/rag_index.py",
             ROOT / "services/api/uv.lock"]
    return {
        "mode": mode, "commit": git("rev-parse", "HEAD"),
        "working_tree_dirty": bool(git("status", "--porcelain")),
        "files_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        "generation_model": os.environ.get("GENERATION_MODEL", "unconfigured"),
        "embedding_model": os.environ.get("EMBEDDING_MODEL", "unconfigured"),
        "k": rag.DEFAULT_K, "min_score": rag.MIN_SCORE,
    }


class AgentService:
    def __init__(self, checkpointer, trace_dir, *, mode="live"):
        self.trace_dir = Path(trace_dir)
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self.provenance = provenance(mode)
        self.graph = build_graph().compile(checkpointer=checkpointer)

    def query(self, question, *, access_token=None):
        from .tools.mcp_incidents import current_access_token
        token = current_access_token.set(access_token)
        try:
            return self._query(question)
        finally:
            current_access_token.reset(token)

    def _query(self, question):
        state = StateContract(question=question).model_dump()
        run_id = str(uuid4())
        trace = Trace(run_id=run_id, question=question, provenance=self.provenance)
        config = {"configurable": {"thread_id": run_id}}
        try:
            save_trace(self.trace_dir, trace)
            for update in self.graph.stream(state, config, stream_mode="updates", durability="sync"):
                for node, output in update.items():
                    state.update(output)
                    trace.events.append(Event(node=node, status="completed", output=output, next_node=next_node(node, state)))
                    save_trace(self.trace_dir, trace)
            StateContract.model_validate(state)
            trace.answer = state["answer"]
            trace.error_code = state["error_code"]
            trace.status = "invalid_question" if state["error_code"] else state["outcome"]
            trace.finished_at = datetime.now(timezone.utc)
            save_trace(self.trace_dir, trace)
        except Exception as exc:
            trace.status, trace.answer, trace.error_code = "failed", None, "agent_unavailable"
            trace.finished_at = datetime.now(timezone.utc)
            trace.events.append(Event(node=exc.node if isinstance(exc, NodeFailure) else "runtime",
                                      status="failed", error_code="agent_unavailable"))
            try:
                save_trace(self.trace_dir, trace)
            except Exception:
                logger.error("agent trace persistence failed run_id=%s", run_id)
            # No raw provider exception: it can contain request data or credentials.
            logger.error("agent run failed run_id=%s node=%s", run_id, trace.events[-1].node)
            raise AgentError("agent_unavailable", run_id) from exc
        logger.info("agent run_id=%s status=%s", run_id, trace.status)
        if trace.error_code:
            raise AgentError(trace.error_code, run_id)
        return trace.answer, run_id


@contextmanager
def open_service(runtime_dir=None, trace_dir=None, *, mode="live"):
    runtime = Path(runtime_dir or os.environ.get("AGENT_RUNTIME_DIR", DEFAULT_RUNTIME))
    runtime.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(runtime / "checkpoints.sqlite"), check_same_thread=False)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        saver = SqliteSaver(connection, serde=JsonPlusSerializer(allowed_msgpack_modules=[]))
        saver.setup()
        yield AgentService(saver, trace_dir or runtime / "traces", mode=mode)
    finally:
        connection.close()
