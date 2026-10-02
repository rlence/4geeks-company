from fastapi import APIRouter, Depends, Path
from sqlmodel import Session
from inventory.database import get_session
from inventory.permissions import read_access, write_access
from inventory.schemas import IngredientCreate, IngredientRead, EntryCreate, EntryRead, ExitCreate, ExitRead, OrderRead, Country
from inventory.service import create_product, create_movement, transaction
from inventory import repository

router = APIRouter(prefix='/inventory', tags=['inventory'])

@router.get('/products', response_model=list[IngredientRead])
def list_products(country: Country | None = None, owner=Depends(read_access), session: Session = Depends(get_session)):
    with transaction(session):
        return repository.products(session, country=country)

@router.post('/products', response_model=IngredientRead, status_code=201)
def post_product(payload: IngredientCreate, owner=Depends(write_access), session: Session = Depends(get_session)):
    return create_product(session, payload)

@router.get('/products/{ingredient_id}', response_model=IngredientRead)
def get_product(ingredient_id: int = Path(gt=0, le=9007199254740991), owner=Depends(read_access), session: Session = Depends(get_session)):
    with transaction(session):
        return repository.products(session, ingredient_id=ingredient_id)[0]

@router.post('/orders/inbound', response_model=EntryRead, status_code=201)
def inbound(payload: EntryCreate, owner=Depends(write_access), session: Session = Depends(get_session)):
    return create_movement(session, payload, owner, outbound=False)

@router.post('/orders/outbound', response_model=ExitRead, status_code=201)
def outbound(payload: ExitCreate, owner=Depends(write_access), session: Session = Depends(get_session)):
    return create_movement(session, payload, owner, outbound=True)

@router.get('/orders', response_model=list[OrderRead], response_model_exclude_none=True)
def list_orders(owner=Depends(read_access), session: Session = Depends(get_session)):
    with transaction(session):
        return repository.orders(session)
