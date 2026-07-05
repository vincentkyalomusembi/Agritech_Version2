"""
KAMIS Data Utilities
====================
Helper functions for cleaning and normalising raw KAMIS price records
before they are matched to database entities (Crop, County) and stored.
"""

from loguru import logger


# Mapping of KAMIS commodity names → our Crop.name values (lowercase match)
CROP_NAME_MAP: dict[str, str] = {
    "maize": "Maize",
    "white maize": "Maize",
    "yellow maize": "Maize",
    "beans": "Beans",
    "dry beans": "Beans",
    "mwitemania beans": "Beans",
    "sorghum": "Sorghum",
    "wheat": "Wheat",
    "rice": "Rice",
    "irish potatoes": "Irish Potatoes",
    "potatoes": "Irish Potatoes",
    "sweet potatoes": "Sweet Potatoes",
    "cassava": "Cassava",
    "millet": "Millet",
    "finger millet": "Millet",
    "green grams": "Green Grams",
    "cow peas": "Cow Peas",
    "pigeon peas": "Pigeon Peas",
    "sunflower": "Sunflower",
    "groundnuts": "Groundnuts",
    "soybeans": "Soybeans",
    "kales": "Kales",
    "sukuma wiki": "Kales",
    "tomatoes": "Tomatoes",
    "onions": "Onions",
    "cabbages": "Cabbages",
    "bananas": "Bananas",
    "avocado": "Avocado",
    "mango": "Mango",
    "oranges": "Oranges",
    "pineapples": "Pineapples",
    "passion fruits": "Passion Fruits",
}


# Mapping of KAMIS county/market names → our County.name values
COUNTY_NAME_MAP: dict[str, str] = {
    "nairobi": "Nairobi",
    "mombasa": "Mombasa",
    "kisumu": "Kisumu",
    "nakuru": "Nakuru",
    "eldoret": "Uasin Gishu",
    "uasin gishu": "Uasin Gishu",
    "meru": "Meru",
    "embu": "Embu",
    "nyeri": "Nyeri",
    "muranga": "Murang'a",
    "murang'a": "Murang'a",
    "kiambu": "Kiambu",
    "machakos": "Machakos",
    "makueni": "Makueni",
    "kajiado": "Kajiado",
    "kitui": "Kitui",
    "kilifi": "Kilifi",
    "kwale": "Kwale",
    "taita taveta": "Taita-Taveta",
    "garissa": "Garissa",
    "wajir": "Wajir",
    "mandera": "Mandera",
    "marsabit": "Marsabit",
    "isiolo": "Isiolo",
    "samburu": "Samburu",
    "trans nzoia": "Trans-Nzoia",
    "bungoma": "Bungoma",
    "kakamega": "Kakamega",
    "vihiga": "Vihiga",
    "busia": "Busia",
    "siaya": "Siaya",
    "homabay": "Homa Bay",
    "homa bay": "Homa Bay",
    "migori": "Migori",
    "kisii": "Kisii",
    "nyamira": "Nyamira",
    "kericho": "Kericho",
    "bomet": "Bomet",
    "nandi": "Nandi",
    "laikipia": "Laikipia",
    "kirinyaga": "Kirinyaga",
    "nyandarua": "Nyandarua",
    "tharaka nithi": "Tharaka-Nithi",
    "tana river": "Tana River",
    "lamu": "Lamu",
    "west pokot": "West Pokot",
    "elgeyo marakwet": "Elgeyo-Marakwet",
    "baringo": "Baringo",
    "turkana": "Turkana",
    "narok": "Narok",
}


def normalise_crop_name(raw: str) -> str | None:
    """
    Map a KAMIS commodity string to the canonical Crop name.
    Returns None if no mapping is found.
    """
    key = raw.strip().lower()
    result = CROP_NAME_MAP.get(key)
    if not result:
        logger.debug(f"KAMIS: No crop mapping for '{raw}'")
    return result


def normalise_county_name(raw: str) -> str | None:
    """
    Map a KAMIS county/market string to the canonical County name.
    Returns None if no mapping is found.
    """
    key = raw.strip().lower()

    # Try direct match
    if key in COUNTY_NAME_MAP:
        return COUNTY_NAME_MAP[key]

    # Try partial match (market names often include county)
    for k, v in COUNTY_NAME_MAP.items():
        if k in key:
            return v

    logger.debug(f"KAMIS: No county mapping for '{raw}'")
    return None
