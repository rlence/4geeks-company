from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from tinydb import Query
from tinydb.table import Document

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
    return _to_supplier_out(suppliers_table.get(doc_id=doc_id))


@router.get("", response_model=list[SupplierOut])
def list_suppliers(
    country: Country | None = None, category: Category | None = None
) -> list[SupplierOut]:
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

    return [_to_supplier_out(doc) for doc in docs]


@router.get("/{supplier_id}", response_model=SupplierOut)
def get_supplier(supplier_id: int) -> SupplierOut:
    return _to_supplier_out(_get_or_404(supplier_id))


@router.patch("/{supplier_id}/rate", response_model=SupplierOut)
def update_rate(supplier_id: int, payload: SupplierRateUpdate) -> SupplierOut:
    _get_or_404(supplier_id)
    now = datetime.now(timezone.utc).isoformat()
    suppliers_table.update(
        {"rate_per_unit": payload.rate_per_unit, "updated_at": now},
        doc_ids=[supplier_id],
    )
    return _to_supplier_out(suppliers_table.get(doc_id=supplier_id))


@router.patch("/{supplier_id}/status", response_model=SupplierOut)
def update_status(supplier_id: int, payload: SupplierStatusUpdate) -> SupplierOut:
    _get_or_404(supplier_id)
    suppliers_table.update({"status": payload.status.value}, doc_ids=[supplier_id])
    return _to_supplier_out(suppliers_table.get(doc_id=supplier_id))


@router.delete("/{supplier_id}", status_code=204)
def delete_supplier(supplier_id: int) -> None:
    _get_or_404(supplier_id)
    suppliers_table.remove(doc_ids=[supplier_id])
