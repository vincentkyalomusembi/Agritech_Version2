import json
import re
from pathlib import Path

from app.counties.model import County

COUNTY_DATA_PATH = Path(__file__).parent / "data" / "counties.json"

COUNTIES = [
    "Baringo",
    "Bomet",
    "Bungoma",
    "Busia",
    "Elgeyo Marakwet",
    "Embu",
    "Garissa",
    "Homa Bay",
    "Isiolo",
    "Kajiado",
    "Kakamega",
    "Kericho",
    "Kiambu",
    "Kilifi",
    "Kirinyaga",
    "Kisii",
    "Kisumu",
    "Kitui",
    "Kwale",
    "Laikipia",
    "Lamu",
    "Machakos",
    "Makueni",
    "Mandera",
    "Marsabit",
    "Meru",
    "Migori",
    "Mombasa",
    "Murang'a",
    "Nairobi",
    "Nakuru",
    "Nandi",
    "Narok",
    "Nyamira",
    "Nyandarua",
    "Nyeri",
    "Samburu",
    "Siaya",
    "Taita Taveta",
    "Tana River",
    "Tharaka Nithi",
    "Trans Nzoia",
    "Turkana",
    "Uasin Gishu",
    "Vihiga",
    "Wajir",
    "West Pokot",
]


def seed_counties(db):
    data = json.loads(COUNTY_DATA_PATH.read_text(encoding="utf-8"))
    existing = db.query(County).all()
    by_key = {_county_key(county.name): county for county in existing}
    for row in data:
        name = row["name"]
        point = row["centroid"]
        county = by_key.get(_county_key(name))
        if county is None:
            # Preserve the project's established spelling for existing counties.
            county = next((by_key.get(_county_key(old_name)) for old_name in COUNTIES if _county_key(old_name) == _county_key(name)), None)
        if county is None:
            county = County(name=name, latitude=point["lat"], longitude=point["lng"])
            db.add(county)
            by_key[_county_key(name)] = county
        elif county.latitude == 0.0 and county.longitude == 0.0:
            county.latitude = point["lat"]
            county.longitude = point["lng"]

    db.commit()

    print(f"{len(data)} county names and centroid coordinates seeded.")


def _county_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())
