import asyncio
from contextvars import ContextVar
from datetime import datetime, timezone
from incidents.repository import IncidentError, TIMEOUT_SECONDS
from incidents.service import get_incident_repository

# Solo identidad validada; el contexto no es parte del estado/checkpoint.
current_owner = ContextVar('incident_owner', default=None)

async def read_incidents(decision, owner):
    if not owner:
        return {'status': 'unauthorized', 'items': []}
    try:
        async with asyncio.timeout(TIMEOUT_SECONDS):
            repo = get_incident_repository()
            if decision.ticket_id:
                items = [await repo.get(owner, decision.ticket_id)]
                total = 1
            else:
                page = await repo.list(owner, status=decision.status, category=decision.category, limit=10)
                items, total = page.items, page.total
            fields = {'id', 'status', 'category', 'origin', 'updated_at', 'resolved_at'}
            return {'status': 'ok', 'items': [i.model_dump(mode='json', include=fields) for i in items],
                    'total': total, 'queried_at': datetime.now(timezone.utc).isoformat()}
    except (TimeoutError, asyncio.TimeoutError):
        return {'status': 'timeout', 'items': []}
    except IncidentError as exc:
        return {'status': exc.code, 'items': []}
    except Exception:
        return {'status': 'unavailable', 'items': []}

def lookup(decision):
    return asyncio.run(read_incidents(decision, current_owner.get()))

def format_result(result):
    if result['status'] != 'ok':
        return {
            'not_found': 'No encontré ese ticket entre tus incidencias accesibles.',
            'unauthorized': 'Necesitas iniciar sesión para consultar tus incidencias.',
        }.get(result['status'], 'No pude confirmar el estado de las incidencias ahora mismo. Inténtalo de nuevo.')
    if not result['items']:
        return 'No encontré incidencias tuyas con esos filtros.'
    names = {'open': 'abierto', 'in_progress': 'en progreso', 'resolved': 'resuelto'}
    lines = [f"Ticket {i['id']}: {names[i['status']]}. Categoría: {i['category']}. Actualizado: {i['updated_at']}." for i in result['items']]
    if result['total'] > len(result['items']):
        lines.append(f"Se muestran {len(result['items'])} de {result['total']} resultados. Acota los filtros en el gestor.")
    return '\n'.join(lines)
