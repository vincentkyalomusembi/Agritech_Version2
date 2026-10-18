from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.database.sessions import get_db
from app.vendors.schema import VendorEventCounts, VendorEventCreate, VendorPage, VendorProductResponse, VendorSummary
from app.vendors.service import VendorService

router = APIRouter(prefix="/vendors", tags=["Vendors"])


def _point(latitude: float | None, longitude: float | None) -> tuple[float, float] | None:
    return (latitude, longitude) if latitude is not None and longitude is not None else None


def _optional_farmer_id(request: Request) -> UUID | None:
    """Attribute events to a signed-in farmer when a valid token is sent; never required."""
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    try:
        return UUID(str(decode_access_token(header[7:]).get("sub")))
    except Exception:
        return None


@router.get("", response_model=VendorPage)
def list_vendors(
    q: str | None = Query(default=None, max_length=100),
    county: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=30),
    product: str | None = Query(default=None, max_length=100),
    latitude: float | None = Query(default=None, ge=-4.7, le=5.1),
    longitude: float | None = Query(default=None, ge=33.9, le=41.9),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Agrovet directory. Sponsored listings come first and are flagged; then nearest first."""
    rows, total = VendorService(db).search(q, county, category, product, _point(latitude, longitude), limit, offset)
    return VendorPage(items=rows, total=total, limit=limit, offset=offset)


@router.get("/{vendor_id}", response_model=VendorSummary)
def get_vendor(
    vendor_id: UUID,
    latitude: float | None = Query(default=None, ge=-4.7, le=5.1),
    longitude: float | None = Query(default=None, ge=33.9, le=41.9),
    db: Session = Depends(get_db),
):
    vendor = VendorService(db).get(vendor_id, _point(latitude, longitude))
    if vendor is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.get("/{vendor_id}/products", response_model=list[VendorProductResponse])
def list_vendor_products(vendor_id: UUID, db: Session = Depends(get_db)):
    service = VendorService(db)
    if service.get(vendor_id) is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return service.products(vendor_id)


@router.post("/{vendor_id}/events", response_model=VendorEventCounts)
def record_vendor_event(
    vendor_id: UUID,
    payload: VendorEventCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """Count a profile view or contact (call, WhatsApp, directions) for listing reports."""
    service = VendorService(db)
    if service.get(vendor_id) is None:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return service.record_event(vendor_id, payload.event, _optional_farmer_id(request))
