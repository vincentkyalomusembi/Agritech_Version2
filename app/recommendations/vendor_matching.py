from math import atan2, cos, radians, sin, sqrt
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.catalogue.model import Vendor, VendorProduct


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * earth_radius_km * atan2(sqrt(a), sqrt(1 - a))


class VendorMatchingService:
    """Find vendors with an actual matching product listing and rank by distance."""

    def __init__(self, db: Session):
        self.db = db

    def match_variety(self, variety_id: UUID, farmer, limit: int = 3) -> list[dict]:
        rows = (
            self.db.query(VendorProduct)
            .options(joinedload(VendorProduct.vendor).joinedload(Vendor.county))
            .filter(VendorProduct.crop_variety_id == variety_id)
            .all()
        )
        farmer_lat = getattr(farmer, "latitude", None)
        farmer_lon = getattr(farmer, "longitude", None)
        ranked = []
        for row in rows:
            vendor = row.vendor
            if not vendor:
                continue
            distance = None
            if farmer_lat is not None and farmer_lon is not None and vendor.latitude is not None and vendor.longitude is not None:
                distance = distance_km(farmer_lat, farmer_lon, vendor.latitude, vendor.longitude)
            same_county = vendor.county_id == farmer.county_id
            # Do not describe an unlocated vendor as nearest. County matches
            # remain useful but are explicitly identified as distance unknown.
            ranked.append((0 if distance is not None else 1, distance if distance is not None else 0 if same_county else 1e9, row, vendor))
        ranked.sort(key=lambda item: (item[0], item[1]))
        return [
            {
                "product_id": str(row.id),
                "vendor_id": str(vendor.id),
                "name": vendor.name,
                "county": vendor.county.name if vendor.county else None,
                "address": vendor.address,
                "phone": vendor.contact_phone,
                "product": row.product_name,
                "price_kes": float(row.price_kes) if row.price_kes is not None else None,
                "unit": row.unit,
                "stock_quantity": row.stock_quantity,
                "distance_km": round(distance, 1) if (distance := (distance_km(farmer_lat, farmer_lon, vendor.latitude, vendor.longitude) if farmer_lat is not None and farmer_lon is not None and vendor.latitude is not None and vendor.longitude is not None else None)) is not None else None,
            }
            for _, _, row, vendor in ranked[:limit]
        ]
