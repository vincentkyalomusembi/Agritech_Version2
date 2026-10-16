"""Resolve the best available coordinates for a farmer-specific lookup."""


def farmer_coordinates(farmer) -> tuple[float | None, float | None, str]:
    """Prefer a map pin, then a ward's parent constituency centroid, then county centroid."""
    if farmer.latitude is not None and farmer.longitude is not None:
        return farmer.latitude, farmer.longitude, "farm_pin"
    constituency = getattr(farmer, "constituency", None)
    if constituency is None:
        selected_ward = getattr(farmer, "selected_ward", None)
        constituency = getattr(selected_ward, "constituency", None) if selected_ward else None
    if constituency is not None:
        return constituency.latitude, constituency.longitude, "constituency_centroid"
    county = getattr(farmer, "county", None)
    return getattr(county, "latitude", None), getattr(county, "longitude", None), "county_centroid"
