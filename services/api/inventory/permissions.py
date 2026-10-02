"""Capacidades del servidor. La ausencia de asignación nunca concede acceso."""
import json
import os
from fastapi import Depends, Request
from auth import get_current_user
from database import users_table
from .errors import InventoryError, unavailable


def capabilities(owner: str) -> set[str]:
    try:
        configured = os.environ.get('INVENTORY_PERMISSIONS')
        if configured is not None:
            mapping = json.loads(configured)
        else:
            # Asignación administrativa persistida, nunca tomada del JWT o del cliente.
            user = users_table.get(doc_id=int(owner)) if owner.isdecimal() else None
            mapping = {owner: user.get('inventory_permissions', []) if user else []}
        allowed = {'inventory:read', 'inventory:write'}
        if not isinstance(mapping, dict) or any(
            not isinstance(k, str) or not isinstance(v, list) or
            any(not isinstance(x, str) or x not in allowed for x in v)
            for k, v in mapping.items()
        ):
            raise ValueError()
        return set(mapping.get(owner, []))
    except (ValueError, TypeError):
        raise unavailable() from None


def require(scope):
    def check(request: Request, user=Depends(get_current_user)):
        request.state.inventory_owner = str(user.doc_id)
        granted = capabilities(str(user.doc_id))
        required = {scope, 'inventory:read'}
        if not required <= granted:
            raise InventoryError(403, 'inventory_forbidden', 'No tienes permiso para esta operación de inventario.')
        return str(user.doc_id)
    return check

read_access = require('inventory:read')
write_access = require('inventory:write')
