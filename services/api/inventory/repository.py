from decimal import Decimal
from sqlalchemy import func
from sqlmodel import Session, select
from .models import Ingredient, IngredientEntry, IngredientExit
from .errors import InventoryError


def products(session: Session, ingredient_id=None, country=None):
    # Agregar antes del JOIN: dos entradas y tres salidas no deben multiplicarse entre sí.
    entries = select(IngredientEntry.ingredient_id, func.sum(IngredientEntry.quantity).label('qty')).group_by(IngredientEntry.ingredient_id).subquery()
    exits = select(IngredientExit.ingredient_id, func.sum(IngredientExit.quantity).label('qty')).group_by(IngredientExit.ingredient_id).subquery()
    stock = (func.coalesce(entries.c.qty, 0) - func.coalesce(exits.c.qty, 0)).label('stock')
    query = select(Ingredient, stock).outerjoin(entries, entries.c.ingredient_id == Ingredient.id).outerjoin(exits, exits.c.ingredient_id == Ingredient.id).order_by(Ingredient.id)
    if ingredient_id is not None:
        query = query.where(Ingredient.id == ingredient_id)
    if country is not None:
        query = query.where(Ingredient.country == country)
    result = [{**item.model_dump(), 'current_stock': balance} for item, balance in session.exec(query).all()]
    if ingredient_id is not None and not result:
        raise InventoryError(404, 'ingredient_not_found', 'Ingrediente no encontrado.')
    return result


def lock_ingredient(session: Session, ingredient_id: int):
    ingredient = session.exec(select(Ingredient).where(Ingredient.id == ingredient_id).with_for_update()).first()
    if ingredient is None:
        raise InventoryError(404, 'ingredient_not_found', 'Ingrediente no encontrado.')
    return ingredient


def balance(session: Session, ingredient_id: int):
    # Una única sentencia observa un snapshot consistente de ambas tablas.
    inbound = select(func.coalesce(func.sum(IngredientEntry.quantity), 0)).where(IngredientEntry.ingredient_id == ingredient_id).scalar_subquery()
    outbound = select(func.coalesce(func.sum(IngredientExit.quantity), 0)).where(IngredientExit.ingredient_id == ingredient_id).scalar_subquery()
    return Decimal(session.exec(select(inbound - outbound)).one())


def orders(session: Session):
    results = []
    for model, kind in ((IngredientEntry, 'inbound'), (IngredientExit, 'outbound')):
        for item, ingredient in session.exec(select(model, Ingredient).join(Ingredient, model.ingredient_id == Ingredient.id)).all():
            results.append({**item.model_dump(), 'type': kind, 'ingredient_name': ingredient.name, 'unit': ingredient.unit})
    return sorted(results, key=lambda x: (x['created_at'], x['type'], x['id']), reverse=True)
