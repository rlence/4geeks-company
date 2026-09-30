import asyncio
from concurrent.futures import ThreadPoolExecutor
import pytest
from support_agent import routing
from support_agent.contracts import Decision
from support_agent.graph import rag
from support_agent.service import open_service
from support_agent.traces import load_trace
from support_agent.tools import incidents
from incidents.schemas import Incident
from incidents.repository import IncidentError

ROW=dict(id=482,title='Ticket de prueba',description='Prueba controlada',category='technical',status='open',origin='api',created_by='7',created_at='2026-09-30T10:00:00Z',updated_at='2026-09-30T10:00:00Z',resolved_at=None,version=1)

@pytest.fixture
def sources(monkeypatch):
    seen=[]
    class Repo:
        async def get(self,owner,ticket_id):
            seen.append((owner,ticket_id))
            return Incident(**ROW)
    monkeypatch.setattr(incidents,'get_incident_repository',lambda:Repo())
    monkeypatch.setattr(rag,'retrieve',lambda q:[{'text':'Oro: 50 puntos','source_document':'loyalty-program'}])
    monkeypatch.setattr(rag,'generate_answer',lambda q,c:'Oro: 50 puntos.')
    return seen

def run_case(tmp_path,monkeypatch,decision,owner='7'):
    monkeypatch.setattr(routing,'classify',lambda q:decision)
    with open_service(tmp_path,mode='mock') as service:
        answer,run=service.query('Pregunta',owner=owner)
    return answer,load_trace(tmp_path/'traces'/f'{run}.json')

def test_tool_only_never_retrieves(tmp_path,monkeypatch,sources):
    monkeypatch.setattr(rag,'retrieve',lambda q:pytest.fail('No RAG para datos operativos'))
    answer,trace=run_case(tmp_path,monkeypatch,Decision(source='incidents',ticket_id=482))
    assert 'abierto' in answer and sources==[('7',482)]
    assert [e.node for e in trace.events]==['receive_question','classify_request','lookup_incident','answer_incident']
    assert [e.next_node for e in trace.events]==['classify_request','lookup_incident','answer_incident','END']
    assert 'created_by' not in trace.model_dump_json()

@pytest.mark.parametrize('code',['not_found','timeout','unavailable','unauthorized','invalid_response'])
def test_fallback_trace(tmp_path,monkeypatch,sources,code):
    class Repo:
        async def get(self,*args):raise IncidentError(code)
    monkeypatch.setattr(incidents,'get_incident_repository',lambda:Repo())
    answer,trace=run_case(tmp_path,monkeypatch,Decision(source='incidents',ticket_id=482))
    assert trace.status=='fallback' and trace.events[-1].node=='tool_fallback'
    assert 'abierto' not in answer and 'resuelto' not in answer

def test_anonymous_tool_does_not_query_backend(tmp_path,monkeypatch,sources):
    answer,trace=run_case(tmp_path,monkeypatch,Decision(source='incidents',ticket_id=482),owner=None)
    assert not sources and 'iniciar sesión' in answer

@pytest.mark.parametrize('failure',['tool','rag',None])
def test_mixed_sources_and_partial_results(tmp_path,monkeypatch,sources,failure):
    if failure=='tool':monkeypatch.setattr(incidents,'lookup',lambda d:{'status':'timeout','items':[]})
    if failure=='rag':monkeypatch.setattr(rag,'retrieve',lambda q:(_ for _ in ()).throw(RuntimeError('PRIVATE')))
    answer,trace=run_case(tmp_path,monkeypatch,Decision(source='both',ticket_id=482,rag_question='Oro?'))
    assert trace.events[-1].node=='combine_answer'
    assert trace.status==('partial' if failure else 'completed')
    assert 'PRIVATE' not in answer
    assert ('abierto' in answer)==(failure!='tool')
    assert ('50' in answer)==(failure!='rag')

def test_identity_is_request_scoped_under_concurrency(tmp_path,monkeypatch,sources):
    monkeypatch.setattr(routing,'classify',lambda q:Decision(source='incidents',ticket_id=int(q)))
    with open_service(tmp_path,mode='mock') as service:
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda i:service.query(str(i),owner=str(i)),range(1,9)))
    assert sorted(sources)==[(str(i),i) for i in range(1,9)]
    assert incidents.current_owner.get() is None
    assert len({run for _,run in results})==8

def test_deadline_includes_entire_tool(monkeypatch):
    cancelled=[]
    class Repo:
        async def get(self,*a):
            try:await asyncio.sleep(10)
            finally:cancelled.append(True)
    monkeypatch.setattr(incidents,'get_incident_repository',lambda:Repo())
    monkeypatch.setattr(incidents,'TIMEOUT_SECONDS',0.02)
    result=asyncio.run(incidents.read_incidents(Decision(source='incidents',ticket_id=482),'7'))
    assert result['status']=='timeout' and cancelled

@pytest.mark.parametrize('source,node',[('clarify','clarify_request'),('readonly','clarify_request'),('unavailable','routing_fallback')])
def test_non_execution_routes(tmp_path,monkeypatch,sources,source,node):
    _,trace=run_case(tmp_path,monkeypatch,Decision(source=source))
    assert not sources and trace.events[-1].node==node
