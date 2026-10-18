from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.catalogue.model import Vendor, VendorEvent, VendorProduct
from app.counties.model import County
from app.recommendations.vendor_matching import distance_km
from app.vendors.hours import parse_opening_hours, stock_status

CONTACT_EVENTS = ("call", "whatsapp", "directions", "contact")
# Repeat events from the same farmer inside this window are counted once.
EVENT_DEDUP_WINDOW = timedelta(hours=1)


def product_category(product: VendorProduct) -> str:
    if product.category:
        return product.category
    if product.crop_variety_id:
        return "seeds"
    if product.livestock_breed_id:
        return "livestock"
    return "inputs"


class VendorService:
    def __init__(self, db: Session):
        self.db = db

    def summary(self, vendor: Vendor, product_count: int = 0, point: tuple[float, float] | None = None) -> dict:
        distance = None
        if point and vendor.latitude is not None and vendor.longitude is not None:
            distance = round(distance_km(point[0], point[1], vendor.latitude, vendor.longitude), 1)
        return {
            "id": vendor.id, "name": vendor.name, "county": vendor.county.name if vendor.county else None,
            "sub_county": vendor.sub_county, "ward": vendor.ward, "address": vendor.address,
            "latitude": vendor.latitude, "longitude": vendor.longitude,
            "phone": vendor.contact_phone, "whatsapp": vendor.whatsapp_phone, "email": vendor.contact_email,
            "certified": vendor.certified, "sponsored": vendor.sponsored, "categories": vendor.categories or [],
            "opening_hours_text": vendor.opening_hours, "opening_hours": parse_opening_hours(vendor.opening_hours),
            "distance_km": distance, "product_count": product_count,
        }

    def search(self, text: str | None = None, county: str | None = None, category: str | None = None,
               product: str | None = None, point: tuple[float, float] | None = None,
               limit: int = 20, offset: int = 0) -> tuple[list[dict], int]:
        query = self.db.query(Vendor).options(joinedload(Vendor.county))
        if county:
            query = query.join(County, Vendor.county_id == County.id).filter(func.lower(County.name) == county.strip().lower())
        if text:
            pattern = f"%{text.strip()}%"
            query = query.filter(or_(Vendor.name.ilike(pattern), Vendor.address.ilike(pattern), Vendor.ward.ilike(pattern), Vendor.sub_county.ilike(pattern)))
        if product:
            matching = self.db.query(VendorProduct.vendor_id).filter(VendorProduct.product_name.ilike(f"%{product.strip()}%"))
            query = query.filter(Vendor.id.in_(matching))
        vendors = query.all()

        counts = dict(self.db.query(VendorProduct.vendor_id, func.count(VendorProduct.id)).group_by(VendorProduct.vendor_id).all())
        rows = [self.summary(vendor, counts.get(vendor.id, 0), point) for vendor in vendors]
        if category:
            # Category may come from the vendor listing or from what it stocks.
            listed = self.db.query(VendorProduct).filter(VendorProduct.vendor_id.in_([vendor.id for vendor in vendors])).all()
            stocked = {item.vendor_id for item in listed if product_category(item) == category}
            rows = [row for row in rows if category in row["categories"] or row["id"] in stocked]
        # Sponsored listings come first (clients must label them), then nearest, then name.
        rows.sort(key=lambda row: (not row["sponsored"], row["distance_km"] is None, row["distance_km"] or 0, row["name"].lower()))
        return rows[offset:offset + limit], len(rows)

    def get(self, vendor_id: UUID, point: tuple[float, float] | None = None) -> dict | None:
        vendor = self.db.query(Vendor).options(joinedload(Vendor.county)).filter_by(id=vendor_id).first()
        if vendor is None:
            return None
        count = self.db.query(VendorProduct).filter_by(vendor_id=vendor_id).count()
        return self.summary(vendor, count, point)

    def products(self, vendor_id: UUID) -> list[dict]:
        rows = self.db.query(VendorProduct).filter_by(vendor_id=vendor_id).order_by(VendorProduct.product_name).all()
        return [{
            "id": row.id, "vendor_id": row.vendor_id, "name": row.product_name, "category": product_category(row),
            "price_kes": float(row.price_kes) if row.price_kes is not None else None, "unit": row.unit,
            "stock_status": stock_status(row.stock_quantity),
            "price_checked_on": row.price_checked_on.isoformat() if row.price_checked_on else None,
            "crop_variety_id": row.crop_variety_id, "livestock_breed_id": row.livestock_breed_id,
        } for row in rows]

    def record_event(self, vendor_id: UUID, event: str, farmer_id: UUID | None) -> dict:
        if farmer_id is not None:
            since = datetime.now(timezone.utc) - EVENT_DEDUP_WINDOW
            duplicate = self.db.query(VendorEvent.id).filter(
                VendorEvent.vendor_id == vendor_id, VendorEvent.farmer_id == farmer_id,
                VendorEvent.event_type == event, VendorEvent.created_at >= since,
            ).first()
        else:
            duplicate = None
        if duplicate is None:
            self.db.add(VendorEvent(vendor_id=vendor_id, farmer_id=farmer_id, event_type=event))
            self.db.commit()
        return self.counts(vendor_id)

    def counts(self, vendor_id: UUID) -> dict:
        rows = dict(self.db.query(VendorEvent.event_type, func.count(VendorEvent.id))
                    .filter(VendorEvent.vendor_id == vendor_id).group_by(VendorEvent.event_type).all())
        return {"views": rows.get("view", 0), "contacts": sum(rows.get(kind, 0) for kind in CONTACT_EVENTS)}
