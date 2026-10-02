"""Semilla transaccional de desarrollo: nunca se ejecuta al arrancar."""
from sqlalchemy import text
from sqlmodel import select
from .models import Ingredient
from .schemas import EntryCreate, ExitCreate
from .service import transaction, add_movement

VERSION = 'brasaland-inventory-v1'
INGREDIENTS = [
 ('Falda de ternera','BRS-BEEF-001','kg','meat','CO'),
 ('Costilla de cerdo','BRS-PORK-001','kg','meat','US'),
 ('Chimichurri','BRS-SAUCE-001','litro','sauce','CO'),
 ('Salsa BBQ de la casa','BRS-SAUCE-002','litro','sauce','US'),
 ('Yuca','BRS-PROD-001','kg','produce','CO'),
 ('Caja para llevar (M)','BRS-PKG-001','unidad','packaging','CO'),
]


def seed(session, owner):
    with transaction(session):
        # Serializar dos invocaciones del comando, incluso antes de que exista la marca.
        session.execute(text('SELECT pg_advisory_xact_lock(824001)'))
        if session.execute(text('SELECT version FROM inventory.seed_runs WHERE version=:v'), {'v': VERSION}).first():
            return False
        ids = {}
        for name, sku, unit, category, country in INGREDIENTS:
            item = session.exec(select(Ingredient).where(Ingredient.sku == sku)).first()
            expected = dict(name=name, sku=sku, unit=unit, category=category, country=country)
            if item and any(getattr(item,k) != v for k,v in expected.items()):
                raise ValueError('Un SKU existente no coincide con la semilla; no se modificó.')
            if not item:
                item = Ingredient(**expected)
                session.add(item)
                session.flush()
            ids[sku] = item.id
        for sku, qty, supplier in [('BRS-BEEF-001',50,'Carnes del Valle S.A.'),('BRS-BEEF-001',30,'Carnes del Valle S.A.'),('BRS-PORK-001',40,'MiamiMeat Co.'),('BRS-SAUCE-001',20,'Salsas Artesanales Ltda.')]:
            add_movement(session, EntryCreate(ingredient_id=ids[sku], quantity=qty, supplier_name=supplier, location_id=1, user_uuid=owner), owner, outbound=False)
        for sku, qty, reason in [('BRS-BEEF-001',10,'consumption'),('BRS-PORK-001',5,'consumption'),('BRS-SAUCE-001',2,'waste')]:
            add_movement(session, ExitCreate(ingredient_id=ids[sku], quantity=qty, reason=reason, location_id=1, user_uuid=owner), owner, outbound=True)
        session.execute(text('INSERT INTO inventory.seed_runs(version,user_uuid) VALUES (:v,:u)'), {'v':VERSION,'u':owner})
    return True
