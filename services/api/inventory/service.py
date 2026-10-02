from contextlib import contextmanager
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from .database import set_limits
from .errors import InventoryError, unavailable
from .models import Ingredient, IngredientEntry, IngredientExit
from . import repository


@contextmanager
def transaction(session):
    try:
        with session.begin():
            set_limits(session)
            yield
    except IntegrityError as exc:
        if getattr(exc.orig, 'sqlstate', None) == '23505':
            raise InventoryError(409, 'duplicate_sku', 'Ya existe un ingrediente con ese SKU.') from None
        raise unavailable() from None
    except SQLAlchemyError:
        raise unavailable() from None


def create_product(session, payload):
    with transaction(session):
        item = Ingredient(**payload.model_dump())
        session.add(item)
        session.flush()
        result = {**item.model_dump(), 'current_stock': 0}
    return result


def add_movement(session, payload, owner, *, outbound):
    """El llamador abre la transacción. Se comparte con la semilla transaccional."""
    if payload.user_uuid != owner:
        raise InventoryError(403, 'inventory_identity_mismatch', 'No puedes atribuir un movimiento a otro usuario.')
    item = repository.lock_ingredient(session, payload.ingredient_id)
    if outbound:
        available = repository.balance(session, item.id)
        if payload.quantity > available:
            raise InventoryError(400, 'insufficient_stock',
                f"Insufficient stock for ingredient '{item.name}'. Available: {available:f}, requested: {payload.quantity:f}.")
    model = IngredientExit if outbound else IngredientEntry
    movement = model(**{**payload.model_dump(), 'user_uuid': owner})
    session.add(movement)
    session.flush()
    session.refresh(movement)
    return movement.model_dump()


def create_movement(session, payload, owner, *, outbound):
    with transaction(session):
        result = add_movement(session, payload, owner, outbound=outbound)
    return result
