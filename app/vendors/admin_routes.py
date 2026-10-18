from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import write_audit
from app.catalogue.model import Vendor, VendorEvent, VendorProduct
from app.database.sessions import get_db
from app.staff.dependencies import get_current_staff, require_roles
from app.staff.model import StaffRole, StaffUser
from app.vendors.admin_schema import (
    VendorCreate, VendorProductCreate, VendorProductWrite, VendorRanking, VendorReport, VendorWrite,
)
from app.vendors.schema import VendorPage, VendorProductResponse, VendorSummary
from app.vendors.service import CONTACT_EVENTS, VendorService

router = APIRouter(prefix="/admin", tags=["Admin Vendors"])
admin_only = require_roles(StaffRole.PLATFORM_ADMIN)


def _vendor_or_404(db: Session, vendor_id: UUID) -> Vendor:
    vendor = db.query(Vendor).filter_by(id=vendor_id).first()
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


def _since(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


@router.get("/vendors", response_model=VendorPage)
def admin_list_vendors(
    q: str | None = Query(default=None, max_length=100),
    county: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: StaffUser = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    rows, total = VendorService(db).search(q, county, None, None, None, limit, offset)
    return VendorPage(items=rows, total=total, limit=limit, offset=offset)


@router.post("/vendors", response_model=VendorSummary, status_code=201)
def admin_create_vendor(payload: VendorCreate, staff: StaffUser = Depends(admin_only), db: Session = Depends(get_db)):
    data = payload.model_dump(exclude_none=True)
    data.setdefault("source_url", f"admin-entry:{staff.id}")
    vendor = Vendor(**data)
    db.add(vendor)
    db.flush()
    write_audit(db, action="vendor.create", entity="vendor", entity_id=vendor.id, actor_id=staff.id, commit=True)
    return VendorService(db).get(vendor.id)


@router.patch("/vendors/{vendor_id}", response_model=VendorSummary)
def admin_update_vendor(vendor_id: UUID, payload: VendorWrite, staff: StaffUser = Depends(admin_only), db: Session = Depends(get_db)):
    vendor = _vendor_or_404(db, vendor_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(vendor, field, value)
    write_audit(db, action="vendor.update", entity="vendor", entity_id=vendor.id, actor_id=staff.id,
                metadata={"fields": sorted(changes)}, commit=True)
    return VendorService(db).get(vendor.id)


@router.get("/vendors/{vendor_id}/products", response_model=list[VendorProductResponse])
def admin_vendor_products(vendor_id: UUID, _: StaffUser = Depends(get_current_staff), db: Session = Depends(get_db)):
    _vendor_or_404(db, vendor_id)
    return VendorService(db).products(vendor_id)


@router.post("/vendors/{vendor_id}/products", response_model=VendorProductResponse, status_code=201)
def admin_create_vendor_product(vendor_id: UUID, payload: VendorProductCreate, staff: StaffUser = Depends(admin_only), db: Session = Depends(get_db)):
    _vendor_or_404(db, vendor_id)
    product = VendorProduct(vendor_id=vendor_id, **payload.model_dump(exclude_none=True))
    today = datetime.now(timezone.utc).date()
    product.price_checked_on = today if product.price_kes is not None else None
    product.stock_checked_on = today if product.stock_quantity is not None else None
    db.add(product)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This vendor already lists a product with that name, or it links both a variety and a breed.") from exc
    write_audit(db, action="vendor_product.create", entity="vendor_product", entity_id=product.id, actor_id=staff.id, commit=True)
    return next(row for row in VendorService(db).products(vendor_id) if row["id"] == product.id)


@router.patch("/vendor-products/{product_id}", response_model=VendorProductResponse)
def admin_update_vendor_product(product_id: UUID, payload: VendorProductWrite, staff: StaffUser = Depends(admin_only), db: Session = Depends(get_db)):
    product = db.query(VendorProduct).filter_by(id=product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(product, field, value)
    today = datetime.now(timezone.utc).date()
    if "price_kes" in changes:
        product.price_checked_on = today
    if "stock_quantity" in changes:
        product.stock_checked_on = today
    try:
        write_audit(db, action="vendor_product.update", entity="vendor_product", entity_id=product.id, actor_id=staff.id,
                    metadata={"fields": sorted(changes)}, commit=True)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflicting product name or catalogue link.") from exc
    return next(row for row in VendorService(db).products(product.vendor_id) if row["id"] == product.id)


@router.delete("/vendor-products/{product_id}", status_code=204)
def admin_delete_vendor_product(product_id: UUID, staff: StaffUser = Depends(admin_only), db: Session = Depends(get_db)):
    product = db.query(VendorProduct).filter_by(id=product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    write_audit(db, action="vendor_product.delete", entity="vendor_product", entity_id=product_id, actor_id=staff.id, commit=True)


@router.get("/vendor-reports", response_model=list[VendorRanking])
def admin_vendor_rankings(
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=20, ge=1, le=100),
    _: StaffUser = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """Vendors ranked by farmer contacts, then views, over the period."""
    rows = (
        db.query(Vendor, func.count(VendorEvent.id).filter(VendorEvent.event_type == "view"),
                 func.count(VendorEvent.id).filter(VendorEvent.event_type.in_(CONTACT_EVENTS)))
        .join(VendorEvent, VendorEvent.vendor_id == Vendor.id)
        .filter(VendorEvent.created_at >= _since(days))
        .group_by(Vendor.id)
        .all()
    )
    ranked = sorted(rows, key=lambda row: (row[2], row[1]), reverse=True)[:limit]
    return [VendorRanking(vendor_id=vendor.id, name=vendor.name, county=vendor.county.name if vendor.county else None,
                          sponsored=vendor.sponsored, views=views, contacts=contacts)
            for vendor, views, contacts in ranked]


@router.get("/vendors/{vendor_id}/report", response_model=VendorReport)
def admin_vendor_report(
    vendor_id: UUID,
    days: int = Query(default=30, ge=1, le=365),
    _: StaffUser = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """Engagement a listing generated: the evidence shared with the vendor."""
    vendor = _vendor_or_404(db, vendor_id)
    events = db.query(VendorEvent).filter(VendorEvent.vendor_id == vendor_id, VendorEvent.created_at >= _since(days)).all()
    by_type = {kind: sum(1 for event in events if event.event_type == kind) for kind in ("view", *CONTACT_EVENTS)}
    contacts = sum(by_type[kind] for kind in CONTACT_EVENTS)
    daily: dict = {}
    for event in events:
        day = event.created_at.date()
        bucket = daily.setdefault(day, {"date": day, "views": 0, "contacts": 0})
        bucket["views" if event.event_type == "view" else "contacts"] += 1
    return VendorReport(
        vendor_id=vendor.id, name=vendor.name, sponsored=vendor.sponsored, days=days,
        views=by_type["view"], contacts=contacts, calls=by_type["call"], whatsapp=by_type["whatsapp"],
        directions=by_type["directions"],
        unique_farmers=len({event.farmer_id for event in events if event.farmer_id}),
        contact_rate=round(contacts / by_type["view"], 3) if by_type["view"] else None,
        daily=sorted(daily.values(), key=lambda row: row["date"]),
    )
