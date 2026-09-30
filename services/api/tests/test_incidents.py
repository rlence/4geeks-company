from types import SimpleNamespace
import pytest
from auth import get_current_user
from main import app
from incidents.service import get_incident_repository
from incidents.repository import IncidentError
from incidents.schemas import Incident, IncidentList
from test_incidents_repository import ROW

class Repository:
    async def create(self, owner, payload):
        assert owner == '7'
        return Incident(**{**ROW,**payload.model_dump()})
    async def get(self, owner, incident_id):
        if owner!='7' or incident_id!=482:raise IncidentError('not_found')
        return Incident(**ROW)
    async def list(self, owner, **filters):
        items=[Incident(**ROW)] if owner=='7' else []
        return IncidentList(items=items,total=len(items),limit=filters['limit'],offset=filters['offset'])
    async def update(self, owner, incident_id, payload):
        await self.get(owner,incident_id)
        if payload.expected_version!=1:raise IncidentError('conflict')
        return Incident(**{**ROW,'status':payload.status,'version':2})

@pytest.fixture
def authenticated():
    app.dependency_overrides[get_current_user]=lambda:SimpleNamespace(doc_id=7)
    app.dependency_overrides[get_incident_repository]=lambda:Repository()
    yield
    app.dependency_overrides.pop(get_current_user,None)
    app.dependency_overrides.pop(get_incident_repository,None)

def test_requires_login(client):
    assert client.get('/api/incidents').status_code==401
    assert client.post('/api/incidents',json={}).status_code==401

def test_contract_and_owner_injection(client,authenticated):
    payload={k:ROW[k] for k in ('title','description','category')}
    assert client.post('/api/incidents',json=payload).status_code==201
    assert client.post('/api/incidents',json={**payload,'created_by':'8'}).status_code==422
    assert client.get('/api/incidents/482').json()['id']==482
    assert client.get('/api/incidents?limit=101').status_code==422
    assert client.patch('/api/incidents/482/status',json={'status':'resolved','expected_version':0}).status_code==422
    assert client.patch('/api/incidents/482/status',json={'status':'resolved','expected_version':2}).status_code==409
    assert client.get('/api/incidents/999').status_code==404

def test_foreign_owner_cannot_read_or_update(client,authenticated):
    app.dependency_overrides[get_current_user]=lambda:SimpleNamespace(doc_id=8)
    assert client.get('/api/incidents').json()['items']==[]
    assert client.get('/api/incidents/482').status_code==404
    assert client.patch('/api/incidents/482/status',json={'status':'resolved','expected_version':1}).status_code==404
