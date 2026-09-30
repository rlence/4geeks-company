from fastapi import APIRouter, Depends, HTTPException, Path, Query
from auth import get_current_user
from incidents.schemas import IncidentCreate, Incident, IncidentList, StatusUpdate, Status, Category
from incidents.repository import IncidentError
from incidents.service import get_incident_repository

router = APIRouter(prefix='/api/incidents', tags=['incidents'])

async def public_result(operation):
    try:
        return await operation
    except IncidentError as exc:
        status, message = {
            'not_found': (404, 'Incidencia no encontrada.'),
            'conflict': (409, 'El ticket cambió o la transición no está permitida. Recarga el detalle.'),
        }.get(exc.code, (503, 'No se pudo consultar o guardar la incidencia. Inténtalo de nuevo.'))
        raise HTTPException(status, message) from None

@router.get('', response_model=IncidentList)
async def list_incidents(status: Status | None = None, category: Category | None = None,
                         limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                         user=Depends(get_current_user), repo=Depends(get_incident_repository)):
    return await public_result(repo.list(str(user.doc_id), status=status, category=category, limit=limit, offset=offset))

@router.post('', response_model=Incident, status_code=201)
async def create_incident(payload: IncidentCreate, user=Depends(get_current_user), repo=Depends(get_incident_repository)):
    return await public_result(repo.create(str(user.doc_id), payload))

@router.get('/{incident_id}', response_model=Incident)
async def get_incident(incident_id: int = Path(gt=0, le=9007199254740991), user=Depends(get_current_user), repo=Depends(get_incident_repository)):
    return await public_result(repo.get(str(user.doc_id), incident_id))

@router.patch('/{incident_id}/status', response_model=Incident)
async def update_incident(payload: StatusUpdate, incident_id: int = Path(gt=0, le=9007199254740991),
                          user=Depends(get_current_user), repo=Depends(get_incident_repository)):
    return await public_result(repo.update(str(user.doc_id), incident_id, payload))
