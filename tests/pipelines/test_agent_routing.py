from types import SimpleNamespace
import pytest
from support_agent.contracts import Decision
from support_agent.routing import classify
from support_agent import routing

@pytest.mark.parametrize('payload,source',[
 ('{"source":"incidents","ticket_id":482}','incidents'),
 ('{"source":"incidents"}','clarify'),
 ('{"source":"both","ticket_id":482}','clarify'),
 ('{"source":"both","ticket_id":482,"rag_question":"Puntos Oro?"}','both'),
 ('{"source":"readonly"}','readonly'),
 ('{"source":"anything"}','unavailable'),
 ('{"source":"incidents","ticket_id":"482"}','unavailable'),
 ('not json','unavailable')])
def test_provider_output_is_validated(monkeypatch,payload,source):
    monkeypatch.setenv('GENERATION_MODEL','test')
    fake=SimpleNamespace()
    fake.with_options=lambda **kw:fake
    fake.chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw:SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=payload))])))
    monkeypatch.setattr(routing.rag,'_openai',lambda:fake)
    assert classify('Ticket 482 y política Oro').source==source

def test_provider_failure_routes_to_fallback(monkeypatch):
    monkeypatch.setenv('GENERATION_MODEL','test')
    monkeypatch.setattr(routing.rag,'_openai',lambda:(_ for _ in ()).throw(RuntimeError('secret')))
    assert classify('estado del 482').source=='unavailable'


def test_missing_reference_is_clarified():
    assert Decision(source="incidents").source == "clarify"
