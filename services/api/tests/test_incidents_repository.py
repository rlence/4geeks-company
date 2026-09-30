import asyncio
import json
import httpx
import pytest
from incidents.repository import IncidentRepository, IncidentError
from incidents.schemas import IncidentCreate, StatusUpdate

ROW = dict(id=482, title='Prueba de ticket', description='Descripción de prueba', category='technical',
           status='open', origin='api', created_by='7', created_at='2026-09-30T10:00:00Z',
           updated_at='2026-09-30T10:00:00Z', resolved_at=None, version=1)

def run(coro): return asyncio.run(coro)
def repo(handler): return IncidentRepository('https://example.test', 'server-secret', transport=httpx.MockTransport(handler))

def test_get_and_list_always_scope_owner_and_filters():
    def handler(request):
        assert request.method == 'GET'
        assert request.url.params['created_by'] == 'eq.7'
        if 'id' not in request.url.params:
            assert request.url.params['status'] == 'eq.open'
            assert request.url.params['category'] == 'eq.technical'
            assert request.url.params['limit'] == '20'
        return httpx.Response(200, json=[ROW], headers={'Content-Range': '0-0/1'})
    r = repo(handler)
    assert run(r.get('7',482)).id == 482
    assert run(r.list('7',status='open',category='technical')).total == 1

def test_create_sets_owner_and_update_uses_atomic_version_filter():
    def handler(request):
        data = json.loads(request.content)
        if request.method == 'POST':
            assert data['created_by'] == '7'
            assert 'status' not in data
        else:
            assert request.method == 'PATCH'
            assert request.url.params['created_by'] == 'eq.7'
            assert request.url.params['version'] == 'eq.1'
            assert data == {'status': 'resolved'}
        return httpx.Response(200,json=[ROW])
    r=repo(handler)
    run(r.create('7',IncidentCreate(title=ROW['title'],description=ROW['description'],category='technical')))
    run(r.update('7',482,StatusUpdate(status='resolved',expected_version=1)))

@pytest.mark.parametrize('status,code',[(401,'unauthorized'),(403,'unauthorized'),(500,'unavailable'),(409,'conflict')])
def test_http_errors_are_public_codes(status,code):
    with pytest.raises(IncidentError,match=code): run(repo(lambda r:httpx.Response(status,text='PRIVATE')).get('7',482))

def test_invalid_response_and_absent_are_distinct():
    for body,code in [([], 'not_found'),([{'id':482}], 'invalid_response'),({}, 'invalid_response')]:
        with pytest.raises(IncidentError,match=code):run(repo(lambda r:httpx.Response(200,json=body)).get('7',482))

def test_version_conflict_vs_inaccessible():
    for accessible,code in [(True,'conflict'),(False,'not_found')]:
        def handler(r): return httpx.Response(200,json=[ROW] if r.method=='GET' and accessible else [])
        with pytest.raises(IncidentError,match=code):run(repo(handler).update('7',482,StatusUpdate(status='resolved',expected_version=1)))

def test_total_deadline_cancels_io(monkeypatch):
    import incidents.repository as module
    monkeypatch.setattr(module,'TIMEOUT_SECONDS',0.02)
    cancelled=[]
    async def handler(request):
        try: await asyncio.sleep(10)
        finally: cancelled.append(True)
    with pytest.raises(IncidentError,match='timeout'):run(repo(handler).get('7',482))
    assert cancelled == [True]
