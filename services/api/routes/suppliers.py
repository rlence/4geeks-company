from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from tinydb import Query
from tinydb.table import Document

from cache import TTLCache
from database import suppliers_table
from models import (
    Category,
    Country,
    SupplierCreate,
    SupplierOut,
    SupplierRateUpdate,
    SupplierStatusUpdate,
)

router = APIRouter(prefix="/suppliers", tags=["suppliers"])

# Un solo namespace de caché para toda la tabla suppliers: list y detail
# comparten instancia porque ambas dependen de los mismos datos y se
# invalidan juntas en cualquier escritura (ver funciones de abajo). TTL
# de 30s: es un directorio interno de Compras y Proveedores, no un feed
# en vivo — una tarifa desactualizada por hasta 30s es aceptable, y en
# la práctica el clear() en cada escritura hace que la ventana real de
# staleness sea casi siempre mucho menor a los 30s.
SUPPLIERS_CACHE_TTL_SECONDS = 30
_suppliers_cache = TTLCache(ttl_seconds=SUPPLIERS_CACHE_TTL_SECONDS)


def _to_supplier_out(doc: Document) -> SupplierOut:
    return SupplierOut(id=doc.doc_id, **doc)


def _get_or_404(supplier_id: int) -> Document:
    doc = suppliers_table.get(doc_id=supplier_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"Proveedor {supplier_id} no encontrado")
    return doc


@router.post("", response_model=SupplierOut, status_code=201)
def create_supplier(payload: SupplierCreate) -> SupplierOut:
    now = datetime.now(timezone.utc).isoformat()
    record = payload.model_dump(mode="json")
    record["updated_at"] = now
    doc_id = suppliers_table.insert(record)
    _suppliers_cache.clear()
    return _to_supplier_out(suppliers_table.get(doc_id=doc_id))


@router.get("", response_model=list[SupplierOut])
def list_suppliers(
    country: Country | None = None, category: Category | None = None
) -> list[SupplierOut]:
    cache_key = ("list", country.value if country else None, category.value if category else None)
    cached = _suppliers_cache.get(cache_key)
    if cached is not None:
        return cached

    query = Query()
    conditions = []
    if country is not None:
        conditions.append(query.country == country.value)
    if category is not None:
        conditions.append(query.categories.test(lambda cats: category.value in cats))

    if not conditions:
        docs = suppliers_table.all()
    else:
        combined = conditions[0]
        for condition in conditions[1:]:
            combined &= condition
        docs = suppliers_table.search(combined)

    result = [_to_supplier_out(doc) for doc in docs]
    _suppliers_cache.set(cache_key, result)
    return result


@router.get("/{supplier_id}", response_model=SupplierOut)
def get_supplier(supplier_id: int) -> SupplierOut:
    cache_key = ("detail", supplier_id)
    cached = _suppliers_cache.get(cache_key)
    if cached is not None:
        return cached
    result = _to_supplier_out(_get_or_404(supplier_id))
    _suppliers_cache.set(cache_key, result)
    return result


@router.patch("/{supplier_id}/rate", response_model=SupplierOut)
def update_rate(supplier_id: int, payload: SupplierRateUpdate) -> SupplierOut:
    _get_or_404(supplier_id)
    now = datetime.now(timezone.utc).isoformat()
    suppliers_table.update(
        {"rate_per_unit": payload.rate_per_unit, "updated_at": now},
        doc_ids=[supplier_id],
    )
    _suppliers_cache.clear()
    return _to_supplier_out(suppliers_table.get(doc_id=supplier_id))


@router.patch("/{supplier_id}/status", response_model=SupplierOut)
def update_status(supplier_id: int, payload: SupplierStatusUpdate) -> SupplierOut:
    _get_or_404(supplier_id)
    suppliers_table.update({"status": payload.status.value}, doc_ids=[supplier_id])
    _suppliers_cache.clear()
    return _to_supplier_out(suppliers_table.get(doc_id=supplier_id))


@router.delete("/{supplier_id}", status_code=204)
def delete_supplier(supplier_id: int) -> None:
    _get_or_404(supplier_id)
    suppliers_table.remove(doc_ids=[supplier_id])
    _suppliers_cache.clear()
