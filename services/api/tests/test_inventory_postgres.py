"""PostgreSQL real aislado. Solo se permite un servidor local dedicado a pruebas.

INVENTORY_TEST_ADMIN_URL=postgresql://...@127.0.0.1:55439/postgres pytest ...
Crea una base con nombre aleatorio y elimina solo esa base al terminar.
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest
from sqlalchemy.engine import make_url
from sqlalchemy import text
from sqlmodel import Session
from inventory.database import make_engine, get_session
from inventory.schemas import IngredientCreate, EntryCreate, ExitCreate
from inventory.service import create_product, create_movement, transaction
from inventory.errors import InventoryError
from inventory import repository
from inventory.seed import seed
from main import app

ROOT=Path(__file__).resolve().parents[3]
MIGRATION=ROOT/'supabase/migrations/20261002012816_inventory_api.sql'

@pytest.fixture(scope='module')
def pg():
    url=os.environ.get('INVENTORY_TEST_ADMIN_URL')
    if not url:pytest.skip('Requiere PostgreSQL de pruebas explícito')
    parsed=make_url(url)
    assert parsed.host in ('127.0.0.1','localhost') and parsed.port==55439, 'Solo cluster local aislado en 55439'
    name='inventory_test_'+uuid4().hex
    admin=psycopg.connect(url,autocommit=True)
    admin.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    dburl=parsed.set(database=name).render_as_string(hide_password=False)
    try:
        with psycopg.connect(dburl) as conn:
            conn.execute(MIGRATION.read_text())
            conn.execute('ALTER ROLE inventory_app LOGIN')
        engine=make_engine(parsed.set(database=name,username='inventory_app',password=None).render_as_string(hide_password=False))
        yield engine,dburl
        engine.dispose()
    finally:
        admin.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
        admin.close()

@pytest.fixture
def store(pg):
    engine,adminurl=pg
    with psycopg.connect(adminurl) as conn:
        conn.execute('TRUNCATE inventory.entries,inventory.exits,inventory.ingredients,inventory.seed_runs RESTART IDENTITY CASCADE')
    def sessions():
        with Session(engine,expire_on_commit=False) as session:yield session
    app.dependency_overrides[get_session]=sessions
    yield engine
    app.dependency_overrides.pop(get_session,None)

@pytest.fixture
def operator(monkeypatch,existing_user,auth_headers):
    owner=str(existing_user['id'])
    monkeypatch.setenv('INVENTORY_PERMISSIONS',json.dumps({owner:['inventory:read','inventory:write']}))
    return owner,auth_headers

PRODUCT=dict(name='Ingrediente de prueba',sku='TEST',unit='kg',category='meat',country='CO')

def prepare(engine,quantity=10):
    with Session(engine,expire_on_commit=False) as s:
        item=create_product(s,IngredientCreate(**PRODUCT))
        create_movement(s,EntryCreate(ingredient_id=item['id'],quantity=quantity,supplier_name='Prueba',location_id=1,user_uuid='1'),'1',outbound=False)
    return item['id']


def test_full_http_lifecycle_and_errors(store,operator,client):
    owner,headers=operator
    res=client.post('/inventory/products',json=PRODUCT,headers=headers)
    assert res.status_code==201,res.text
    item=res.json();assert item['current_stock']==0
    assert client.post('/inventory/products',json=PRODUCT,headers=headers).status_code==409
    payload=dict(ingredient_id=item['id'],quantity=10,supplier_name='Proveedor',location_id=1,user_uuid=owner)
    assert client.post('/inventory/orders/inbound',json=payload,headers=headers).status_code==201
    out={k:v for k,v in payload.items() if k!='supplier_name'};out['reason']='waste';out['quantity']=3
    assert client.post('/inventory/orders/outbound',json=out,headers=headers).status_code==201
    products=client.get('/inventory/products',headers=headers).json()
    assert isinstance(products,list) and products[0]['current_stock']==7
    assert client.get('/inventory/products?country=US',headers=headers).json()==[]
    assert client.get(f"/inventory/products/{item['id']}",headers=headers).json()['current_stock']==7
    assert client.get('/inventory/products/999',headers=headers).status_code==404
    out['quantity']=8
    res=client.post('/inventory/orders/outbound',json=out,headers=headers)
    assert res.status_code==400 and 'Available: 7' in res.json()['detail']
    assert len(client.get('/inventory/orders',headers=headers).json())==2
    out['quantity']=7
    assert client.post('/inventory/orders/outbound',json=out,headers=headers).status_code==201
    assert client.get('/inventory/products',headers=headers).json()[0]['current_stock']==0
    history=client.get('/inventory/orders',headers=headers).json()
    assert {x['type'] for x in history}=={'inbound','outbound'}
    assert all(x['user_uuid']==owner and x['ingredient_name']==PRODUCT['name'] for x in history)


def test_identity_and_unknown_reference(store,operator,client):
    owner,headers=operator
    payload=dict(ingredient_id=999,quantity=1,reason='consumption',location_id=1,user_uuid='other')
    assert client.post('/inventory/orders/outbound',json=payload,headers=headers).status_code==403
    payload['user_uuid']=owner
    assert client.post('/inventory/orders/outbound',json=payload,headers=headers).status_code==404


def test_no_join_multiplication_or_float_drift(store):
    id=prepare(store,Decimal('0.1'))
    with Session(store,expire_on_commit=False) as s:
        create_movement(s,EntryCreate(ingredient_id=id,quantity='0.2',supplier_name='P',location_id=1,user_uuid='1'),'1',outbound=False)
        for _ in range(2):
            create_movement(s,ExitCreate(ingredient_id=id,quantity='0.1',reason='consumption',location_id=1,user_uuid='1'),'1',outbound=True)
        with transaction(s):assert repository.products(s)[0]['current_stock']==Decimal('0.1')


def test_concurrent_exits_cannot_overspend(store):
    id=prepare(store);barrier=Barrier(2)
    def consume():
        with Session(store,expire_on_commit=False) as s:
            barrier.wait(timeout=5)
            try:
                create_movement(s,ExitCreate(ingredient_id=id,quantity=7,reason='consumption',location_id=1,user_uuid='1'),'1',outbound=True)
                return 201
            except InventoryError as exc:return exc.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:consume(),range(2)))
    assert sorted(results)==[201,400]
    with Session(store) as s:
        with transaction(s):assert repository.balance(s,id)==3


def test_rollback_and_reopen(store):
    id=prepare(store)
    with Session(store) as s:
        with pytest.raises(RuntimeError):
            with transaction(s):
                from inventory.service import add_movement
                add_movement(s,ExitCreate(ingredient_id=id,quantity=1,reason='waste',location_id=1,user_uuid='1'),'1',outbound=True)
                raise RuntimeError('rollback')
    store.dispose()  # Reabrir conexiones, sin caché de datos del proceso.
    with Session(store) as s:
        with transaction(s):assert repository.balance(s,id)==10


def test_seed_is_idempotent(store):
    with Session(store,expire_on_commit=False) as s:
        assert seed(s,'1') is True
        assert seed(s,'1') is False
        with transaction(s):
            items=repository.products(s)
            assert len(items)==6
            assert next(x for x in items if x['sku']=='BRS-BEEF-001')['current_stock']==70
            assert len(repository.orders(s))==7


def test_database_constraints_and_least_privilege(store,pg):
    from sqlalchemy.exc import DBAPIError
    with Session(store) as s:
        for statement in ["DELETE FROM inventory.ingredients", "INSERT INTO inventory.ingredients(name,sku,unit,category,country) VALUES ('a','b','kg','wrong','CO')"]:
            with pytest.raises(DBAPIError):
                with s.begin():s.execute(text(statement))
    with psycopg.connect(pg[1]) as conn:
        rows=conn.execute("SELECT relrowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='inventory' AND c.relkind='r'").fetchall()
        assert len(rows)==4 and all(r[0] for r in rows)
