"""Seed Kenya's IEBC county → constituency → ward selection hierarchy."""
import json
from pathlib import Path

from app.counties.model import County, Constituency, Ward

DATA_DIR = Path(__file__).parent / "data"


def seed_administrative_units(db) -> None:
    counties = json.loads((DATA_DIR / "counties.json").read_text(encoding="utf-8"))
    constituencies = json.loads((DATA_DIR / "constituencies.json").read_text(encoding="utf-8"))
    wards = json.loads((DATA_DIR / "wards.json").read_text(encoding="utf-8"))
    if (len(counties), len(constituencies), len(wards)) != (47, 290, 1450):
        raise ValueError("Kenya administrative reference data must contain 47 counties, 290 constituencies, and 1,450 wards.")

    county_rows = db.query(County).all()
    county_by_normalized_name = {"".join(ch for ch in row.name.lower() if ch.isalnum()): row for row in county_rows}
    county_by_code = {}
    for item in counties:
        key = "".join(ch for ch in item["name"].lower() if ch.isalnum())
        county = county_by_normalized_name.get(key)
        if county is None:
            raise ValueError(f"County {item['name']} must be seeded before its constituencies.")
        point = item.get("centroid") or {}
        if county.latitude == 0.0 and county.longitude == 0.0:
            county.latitude = point["lat"]
            county.longitude = point["lng"]
        county_by_code[item["code"]] = county
    db.flush()

    constituency_by_code = {row.code: row for row in db.query(Constituency).all()}
    for item in constituencies:
        county = county_by_code[item["countyCode"]]
        point = item["centroid"]
        row = constituency_by_code.get(item["code"])
        if row is None:
            row = Constituency(code=item["code"], name=item["name"], county_id=county.id,
                               latitude=point["lat"], longitude=point["lng"])
            db.add(row)
            constituency_by_code[item["code"]] = row
        else:
            row.name = item["name"]
            row.county_id = county.id
            row.latitude = point["lat"]
            row.longitude = point["lng"]
    db.flush()

    ward_by_code = {row.code: row for row in db.query(Ward).all()}
    for item in wards:
        constituency = constituency_by_code[item["constituencyCode"]]
        row = ward_by_code.get(item["code"])
        if row is None:
            row = Ward(code=item["code"], name=item["name"], constituency_id=constituency.id)
            db.add(row)
            ward_by_code[item["code"]] = row
        else:
            row.name = item["name"]
            row.constituency_id = constituency.id

    db.commit()
    print("Seeded 290 constituencies and 1,450 wards across Kenya's 47 counties.")
