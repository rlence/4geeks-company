"""Contratos y autorización sin red ni base real."""
import json
from decimal import Decimal

import pytest
from pydantic import ValidationError
from inventory.schemas import EntryCreate, ExitCreate, IngredientCreate, IngredientRead
from inventory.permissions import capabilities
from inventory.errors import InventoryError

ENTRY = dict(ingredient_id=1, quantity=1, supplier_name='Proveedor', location_id=1, user_uuid='1')

@pytest.mark.parametrize('quantity', [0, -1, 'NaN', 'Infinity', '0.0000001', '1000000000000'])
def test_invalid_quantity(quantity):
    with pytest.raises(ValidationError):
        EntryCreate(**{**ENTRY, 'quantity': quantity})

@pytest.mark.parametrize('field,value', [('location_id',0),('location_id',15),('ingredient_id',True),('supplier_name','  '),('user_uuid','')])
def test_invalid_fields(field,value):
    with pytest.raises(ValidationError):
        EntryCreate(**{**ENTRY,field:value})


def test_stock_is_response_only():
    payload=dict(name=' Yuca ',sku='YUCA',unit='kg',category='produce',country='CO')
    assert IngredientCreate(**payload).name=='Yuca'
    with pytest.raises(ValidationError):
        IngredientCreate(**payload,current_stock=10)
    output=IngredientRead(**payload,id=1,current_stock=Decimal('0.3')).model_dump(mode='json')
    assert output['current_stock']==0.3 and isinstance(output['current_stock'],float)


def test_bad_reason():
    with pytest.raises(ValidationError):
        ExitCreate(ingredient_id=1,quantity=1,reason='lost',location_id=1,user_uuid='1')


def test_permissions_fail_closed(monkeypatch):
    monkeypatch.delenv('INVENTORY_PERMISSIONS',raising=False)
    assert capabilities('1')==set()
    monkeypatch.setenv('INVENTORY_PERMISSIONS','{"1": ["admin"]}')
    with pytest.raises(InventoryError):capabilities('1')

@pytest.mark.parametrize('path,method', [('/inventory/products','get'),('/inventory/products','post'),('/inventory/products/1','get'),('/inventory/orders','get'),('/inventory/orders/inbound','post'),('/inventory/orders/outbound','post')])
def test_every_route_requires_login(client,path,method):
    assert getattr(client,method)(path).status_code==401


def test_unassigned_user_denied(client,auth_headers,monkeypatch):
    monkeypatch.setenv('INVENTORY_PERMISSIONS','{}')
    assert client.get('/inventory/products',headers=auth_headers).status_code==403


def test_read_identity_cannot_write(client,auth_headers,existing_user,monkeypatch):
    monkeypatch.setenv('INVENTORY_PERMISSIONS',json.dumps({str(existing_user['id']):['inventory:read']}))
    for path in ['/inventory/products','/inventory/orders/inbound','/inventory/orders/outbound']:
        assert client.post(path,headers=auth_headers,json={}).status_code==403


def test_missing_database_is_honest_503(client,auth_headers,existing_user,monkeypatch):
    from inventory.database import close_engine
    close_engine()
    monkeypatch.delenv('INVENTORY_DATABASE_URL',raising=False)
    monkeypatch.delenv('INVENTORY_ADMIN_DATABASE_URL',raising=False)
    monkeypatch.setenv('INVENTORY_PERMISSIONS',json.dumps({str(existing_user['id']):['inventory:read']}))
    response=client.get('/inventory/products',headers=auth_headers)
    assert response.status_code==503
    assert response.json()['code']=='inventory_unavailable'
    assert response.headers['X-Request-Id']


def test_persisted_permissions_and_explicit_environment_override(monkeypatch, existing_user):
    from database import users_table
    owner = str(existing_user['id'])
    monkeypatch.delenv('INVENTORY_PERMISSIONS', raising=False)
    assert capabilities(owner) == set()
    users_table.update({'inventory_permissions': ['inventory:read', 'inventory:write']}, doc_ids=[existing_user['id']])
    assert capabilities(owner) == {'inventory:read', 'inventory:write'}
    assert capabilities('999999') == set()
    monkeypatch.setenv('INVENTORY_PERMISSIONS', '{}')
    assert capabilities(owner) == set()


def test_existing_connection_fallback_and_runtime_priority(monkeypatch):
    import inventory.database as db
    calls = []
    monkeypatch.setattr(db, 'make_engine', lambda url, **kw: calls.append((url, kw)) or 'engine')
    db.get_engine.cache_clear()
    monkeypatch.delenv('INVENTORY_DATABASE_URL', raising=False)
    monkeypatch.setenv('INVENTORY_ADMIN_DATABASE_URL', 'admin-test')
    assert db.get_engine() == 'engine'
    assert calls[-1] == ('admin-test', {'allow_admin': True})
    db.get_engine.cache_clear()
    monkeypatch.setenv('INVENTORY_DATABASE_URL', 'runtime-test')
    assert db.get_engine() == 'engine'
    assert calls[-1] == ('runtime-test', {})
    db.get_engine.cache_clear()
