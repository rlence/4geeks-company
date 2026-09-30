"""PostgREST con HTTP asíncrono: el plazo total cancela realmente el I/O.

Reutiliza la configuración Supabase del servidor, no su cliente síncrono,
para evitar consultas bloqueadas en un thread tras vencer el timeout.
"""
import asyncio
import httpx
from .schemas import Incident, IncidentList

TIMEOUT_SECONDS = 5.0

class IncidentError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)

class IncidentRepository:
    def __init__(self, url, key, *, transport=None):
        self.url = url.rstrip('/') + '/rest/v1/support_incidents'
        self.key = key
        self.transport = transport

    async def request(self, method, *, params=None, body=None, prefer='return=representation'):
        try:
            async with asyncio.timeout(TIMEOUT_SECONDS):
                async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, transport=self.transport) as client:
                    response = await client.request(method, self.url, params=params, json=body,
                        headers={'apikey': self.key, 'Authorization': f'Bearer {self.key}',
                                 'Prefer': prefer})
                    if response.status_code in (401, 403):
                        raise IncidentError('unauthorized')
                    if response.status_code == 409:
                        raise IncidentError('conflict')
                    response.raise_for_status()
                    return response.json(), response.headers
        except (TimeoutError, httpx.TimeoutException):
            raise IncidentError('timeout') from None
        except httpx.HTTPError:
            raise IncidentError('unavailable') from None
        except (ValueError, TypeError):
            raise IncidentError('invalid_response') from None

    @staticmethod
    def owner(owner):
        if not owner:
            raise IncidentError('unauthorized')
        return {'created_by': f'eq.{owner}'}

    @staticmethod
    def decode(row):
        try:
            return Incident.model_validate(row)
        except (ValueError, TypeError):
            raise IncidentError('invalid_response') from None

    async def get(self, owner, incident_id):
        rows, _ = await self.request('GET', params={**self.owner(owner), 'id': f'eq.{incident_id}', 'select': '*', 'limit': 1})
        if not isinstance(rows, list):
            raise IncidentError('invalid_response')
        if not rows:
            raise IncidentError('not_found')
        return self.decode(rows[0])

    async def list(self, owner, *, status=None, category=None, limit=20, offset=0):
        params = {**self.owner(owner), 'select': '*', 'order': 'created_at.desc,id.desc', 'limit': limit, 'offset': offset}
        if status: params['status'] = f'eq.{status}'
        if category: params['category'] = f'eq.{category}'
        rows, headers = await self.request('GET', params=params, prefer='count=exact')
        try:
            total = int(headers['content-range'].split('/')[-1])
            return IncidentList(items=[self.decode(row) for row in rows], total=total, limit=limit, offset=offset)
        except (KeyError, TypeError, ValueError):
            raise IncidentError('invalid_response') from None

    async def create(self, owner, payload):
        self.owner(owner)
        rows, _ = await self.request('POST', body={**payload.model_dump(), 'created_by': owner})
        if not isinstance(rows, list) or len(rows) != 1:
            raise IncidentError('invalid_response')
        return self.decode(rows[0])

    async def update(self, owner, incident_id, payload):
        # El trigger verifica transición, fechas y versión bajo el lock de la fila.
        rows, _ = await self.request('PATCH', params={**self.owner(owner), 'id': f'eq.{incident_id}',
            'version': f'eq.{payload.expected_version}'}, body={'status': payload.status})
        if not isinstance(rows, list):
            raise IncidentError('invalid_response')
        if not rows:
            await self.get(owner, incident_id)  # 404 si es ajeno/ausente; nunca revelar propietario.
            raise IncidentError('conflict')
        return self.decode(rows[0])
