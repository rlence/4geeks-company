"""Evals offline Parte 2; --agent-traces-dir requiere trazas de proveedores reales."""
import json
from pathlib import Path
import pytest
from support_agent.traces import load_trace

@pytest.fixture(scope='module')
def traces(request):
    supplied=request.config.getoption('--agent-traces-dir')
    directory=Path(supplied) if supplied else Path(__file__).parent/'fixtures/agent-tools-traces'
    manifest=json.loads((directory/'manifest.json').read_text())
    expected='live' if supplied else 'mock'
    assert manifest['mode']==expected
    assert {'tool','rag'} <= manifest['cases'].keys()
    loaded={}
    for case,filename in manifest['cases'].items():
        assert Path(filename).name==filename and filename.endswith('.json')
        trace=load_trace(directory/filename)
        assert trace.provenance['mode']==expected
        assert trace.provenance['files_sha256']
        assert str(trace.run_id)==Path(filename).stem
        assert trace.finished_at>=trace.started_at
        nodes=[e.node for e in trace.events]
        assert [e.next_node for e in trace.events]==nodes[1:]+['END']
        loaded[case]=trace
    assert len({str(t.run_id) for t in loaded.values()})==len(loaded)
    return loaded

def test_incidents_route_uses_tool_without_rag(traces):
    trace=traces['tool'];nodes=[e.node for e in trace.events]
    assert trace.status=='completed'
    assert nodes==['receive_question','classify_request','lookup_incident','answer_incident']
    result=next(e.output['tool_result'] for e in trace.events if e.node=='lookup_incident')
    assert result['status']=='ok' and result['items']
    names={'open':'abierto','in_progress':'en progreso','resolved':'resuelto'}
    for i in result['items']:
        assert f"Ticket {i['id']}: {names[i['status']]}" in trace.answer

def test_rag_route_does_not_call_incidents(traces):
    trace=traces['rag']
    assert trace.status=='completed'
    assert [e.node for e in trace.events]==['receive_question','classify_request','retrieve_context','generate_answer']
    chunks=next(e.output['context'] for e in trace.events if e.node=='retrieve_context')
    assert any(c.get('source_document')=='loyalty-program' and '50' in c['text'] for c in chunks)
    assert '50' in trace.answer and 'puntos' in trace.answer.lower()

def test_fallback_if_captured(traces):
    if 'fallback' not in traces:pytest.skip('Captura opcional de fallback ausente')
    trace=traces['fallback']
    assert trace.status=='fallback' and trace.events[-1].node=='tool_fallback'
    assert 'no pude confirmar' in trace.answer.lower()
    assert 'abierto' not in trace.answer and 'resuelto' not in trace.answer
