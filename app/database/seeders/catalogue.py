"""Small, source-backed Kenya catalogue seed; no generated/fabricated records."""
from datetime import date

import app.models  # noqa: F401 - register all ORM relationships before queries
from app.catalogue.model import CropVariety, LivestockBreed, Market, Vendor, VendorProduct
from app.counties.model import County
from app.crops.model import Crop
from app.livestock.model import Livestock

CHECKED = date(2026, 10, 14)
KEPHIS_2025 = "https://www.kephis.go.ke/sites/default/files/2025-02/NATIONAL%20CROP%20VARIETY%20LIST-%202025%20EDITION.pdf"
KALRO_MAIZE = "https://www.kalro.org/maize/maize-agronomy/"
KALRO_SORGHUM = "https://www.kalro.org/divisions/crops/sorghum/"
KALRO_BEANS = "https://kalroerepository.kalro.org/bitstreams/90823533-117d-42c4-ac0f-5b42646202b7/download"
VMD_RETAILERS = "https://www.vmd.go.ke/retailers"
MARKET_STUDY = "https://cdn.unisg.it/assets/FontefrancescoZocchi_2020_Indigenous-crops-and-cultural-dynamics-in-the-markets-of-Nakuru-County-Kenya.pdf"
TRADE_PORTAL = "https://kenyatradeportal.go.ke/wholesale-retail-markets"

# Altitude/maturity and variety attributes are transcribed from KEPHIS/KALRO.
# Rainfall ranges are left NULL where the source gives an agro-ecological zone
# rather than a defensible numeric threshold.
VARIETIES = [
    ("Maize", "H6213", "Kenya Seed Company", 1500, 2100, None, None, 180, 240, "Highland hybrid; use fresh certified seed; choose only for high-rainfall highlands.", "Trans Nzoia, Uasin Gishu, Nakuru, Kericho, Nandi, Bungoma, Laikipia, Kisii, Narok"),
    ("Maize", "H614D", "Kenya Seed Company", 1500, 2100, None, None, 180, 270, "Highland hybrid; long season and rainfall dependent.", "Highland zones including Nakuru, Uasin Gishu, Trans Nzoia"),
    ("Maize", "DH04", "Kenya Seed Company", 900, 1700, 400, 800, 75, 100, "Short-season dryland variety; drought tolerant; match planting to effective rains.", "Machakos, Kitui, Makueni and other dryland areas"),
    ("Maize", "WE5 117", "KALRO-Katumani", 900, 1800, 400, 800, 105, 135, "Drought tolerant; reported tolerance to gray leaf spot, turcicum leaf blight and maize streak virus.", "Dry transitional and dry-mid altitude eastern, central and Rift Valley sites"),
    ("Maize", "Sungura 301", "Kenya Seed Company", 1000, 1800, 400, 800, 90, 120, "Short-season dryland variety; confirm seed label and local rainfall before planting.", "Dryland areas of Kenya"),
    ("Beans", "Nyota (KAD 02)", "KALRO Katumani", 900, 1800, None, None, 60, 90, "Drought tolerant, early maturing, high iron and zinc; good pod clearance.", "Medium-altitude and drought-prone bean areas"),
    ("Beans", "Angaza (KMR 11)", "KALRO Kandara", 1200, 1900, None, None, 60, 90, "Micronutrient-rich; medium/high altitude; verify local disease pressure and seed source.", "Medium- and high-altitude bean areas"),
    ("Beans", "Rosecoco (GLP 2)", "KALRO / Kenya Seed Company", 1500, 2000, None, None, 60, 90, "Wide adaptation and high yield potential; not described as drought tolerant by source.", "High-altitude bean areas"),
    ("Sorghum", "Gadam", "KALRO", None, None, None, None, 75, 90, "Very early and drought tolerant; source cautions it is for moderately dry to very dry sites.", "Upper and lower eastern Kenya"),
    ("Sorghum", "Seredo", "KALRO", None, None, None, None, 90, 90, "Fairly drought tolerant; verify bird pressure and local market demand.", "Moderately dry eastern and western Kenya"),
]

BREEDS = [
    ("Goats", "Galla", "Adapted to extensive and semi-intensive pastoral/agro-pastoral systems across ASALs; drought/feed stress is a key risk outside its adapted system.", "Northern and eastern ASAL regions"),
    ("Sheep", "Red Maasai", "Indigenous hair sheep; valued by pastoral systems for hardiness and parasite resilience; maintain locally adapted breeding stock.", "Rift Valley pastoral and semi-arid areas"),
    ("Cattle", "Boran", "Beef breed used in Kenyan dryland systems; performance depends on grazing, water, and herd health.", "Arid and semi-arid beef systems"),
    ("Cattle", "Sahiwal", "Tropical dual-purpose breed used in hot environments; cross-breeding may change heat and feed requirements.", "Hotter eastern and northern livestock systems"),
]

# Vendor directory entries are from VMD's public list of authorized veterinary
# medicine retailers (accessed on CHECKED). No private practitioner names or
# personal phone numbers are copied into the application.
VENDORS = [
    ("MavunoVet", "Kaptagat Road, Eldoret", "Uasin Gishu"),
    ("GREBE ENTERPRISES LIMITED NAKURU", "Shawmut Plaza, Mosque Road, Nakuru", "Nakuru"),
    ("WAKULIMA KIAMUNYI", "Grace Plaza, Nakuru-Kabarak Road, Kiamunyi", "Nakuru"),
    ("Riva Agrovet", "Marvic Plaza, Mburu Gichua Road, Nakuru", "Nakuru"),
    ("Samki Agrovet", "Samki Building, Ngata, Njoro Road", "Nakuru"),
    ("MARURA FAT SUPPLIERS AGROVET", "N.K Building, Gilgil-Nakuru Road, Gilgil", "Nakuru"),
    ("BELEA AGROVET-TALA", "Discount Plaza, Tala, Kangundo Road", "Machakos"),
    ("BARASAM AGROVET SUPPLIES", "Linda Complex, Uhuru Street, Machakos", "Machakos"),
    ("JOI AGROVET", "Kaewa, Kanyonyoo-Embu Road", "Machakos"),
    ("TALA POULTRY CENTRE AND AGROVET", "Tala House, Tala Town", "Machakos"),
    ("KENYA FARMERS ASSOCIATION - NAIROBI", "KFA, Haile Selassie Avenue, Nairobi", "Nairobi"),
    ("WAKULIMA LINE LIMITED", "Gogo Mall, Haile Selassie Avenue, Nairobi", "Nairobi"),
    ("KENCHIC POULTRY CENTRE-EXSAN", "Exsan House, Enterprise Road, Nairobi", "Nairobi"),
    ("PREMIUM FARMING FEEDS", "Premium Turitu, Kiambu-Kanunga Road", "Kiambu"),
    ("SHAMMAH FARMERS HUB", "Macharia Building, Mama Ngina Street, Thika", "Kiambu"),
    ("JUBILEE AGROVET", "Kenyatta Road, Gatundu", "Kiambu"),
    ("GreenField Agro & Veterinary Services", "Councillor, Kutus-Ndomba, Kutus", "Kirinyaga"),
    ("Ukulima Agrovet Services LTD.", "Tree Top Building, Market Street, Kerugoya", "Kirinyaga"),
    ("INPUTS TODAY LTD", "Meru-Maua Road, Muriri Market", "Meru"),
    ("KIANJAI FARM SUPPLIES", "Market Stalls, Meru-Maua Road, Kianjai", "Meru"),
    ("ELDOAGRI SOLUTIONS LIMITED", "K.V.D.A Plaza, Sirikwa, Eldoret", "Uasin Gishu"),
    ("MASHAMBANI FARM INPUTS LTD - TAMARIND PLAZA", "Tamarind Plaza, Ronald Ngala Road, Eldoret", "Uasin Gishu"),
    ("Sisibo City Agrovet Limited", "Silver Ways, Oginga Odinga Street, Eldoret", "Uasin Gishu"),
    ("CROWN ROYALE AGROVETERINARY CENTER LIMITED", "Opposite Glory Inn, Kiminini, Ndalu-Brigadier Road", "Trans Nzoia"),
    ("MITRA WHOLESALE AND RETAIL", "Canon Awuor Street, Kakamega", "Kakamega"),
    ("ENOCHEM AGROVET LIMITED", "Kenyoro FCS, Hospital Road, Kisii", "Kisii"),
    ("TEMIK AGROVET", "Township Road, Londiani", "Kericho"),
    ("MAVUENI FARMCARE AGROVET", "Biashara Street, Kilifi", "Kilifi"),
    ("IMPERIAL POULTRY AND AGRIBIONICS LIMITED", "Battery Centre Building, Ronald Ngala Road, Mombasa", "Mombasa"),
    ("KENCHIC POULTRY CENTRE-NYERI", "Rware, off Gakere Road, Nyeri", "Nyeri"),
    ("Farm care Agrovet", "Nakuru-Nyahururu Road, Charagita", "Nyandarua"),
]

MARKETS = [
    ("Nakuru Wakulima Market", "Nakuru", "Nakuru East", "Biashara", -0.28520, 36.07709, MARKET_STUDY),
    ("Ponda Mali Market", "Nakuru", "Nakuru Town East", None, -0.30808, 36.06250, MARKET_STUDY),
    ("Top Market", "Nakuru", "Nakuru Town East", None, -0.28466, 36.07485, MARKET_STUDY),
    ("Naivasha Municipal Market", "Nakuru", "Naivasha", None, -0.71691, 36.43532, MARKET_STUDY),
    ("Naivasha Wholesale Market", "Nakuru", "Naivasha", None, -0.71672, 36.43624, MARKET_STUDY),
    ("Molo City Market", "Nakuru", "Molo", None, -0.24993, 35.73448, MARKET_STUDY),
    ("Wakulima Market", "Nairobi", "Kamukunji", "Kamukunji", -1.28761, 36.83236, "https://www.openstreetmap.org/way/125300906"),
    ("Kibuye Market", "Kisumu", "Kisumu Central", None, -0.09286, 34.76850, "https://www.openstreetmap.org/way/262027048"),
]


def _by_name(db, model, name):
    # Counties in older deployed schemas may not yet have the optional
    # coordinate columns present in the current County ORM mapping. Fetch only
    # the ID needed for foreign keys so this seeder stays schema-compatible.
    return db.query(model.id).filter(model.name.ilike(name)).scalar()


def seed_catalogue(db):
    for crop_name, name, maintainer, amin, amax, rmin, rmax, dmin, dmax, risks, regions in VARIETIES:
        crop = _by_name(db, Crop, crop_name)
        if crop and not db.query(CropVariety).filter_by(crop_id=crop, name=name).first():
            db.add(CropVariety(crop_id=crop, name=name, maintainer=maintainer,
                altitude_min_m=amin, altitude_max_m=amax, rainfall_min_mm=rmin, rainfall_max_mm=rmax,
                maturity_days_min=dmin, maturity_days_max=dmax, risk_attributes=risks,
                adapted_regions=regions, source_url=(KEPHIS_2025 if crop_name in {"Beans", "Maize"} else KALRO_SORGHUM if crop_name == "Sorghum" else KALRO_MAIZE), source_checked_on=CHECKED))
    for animal_name, name, risks, regions in BREEDS:
        animal = _by_name(db, Livestock, animal_name)
        if animal and not db.query(LivestockBreed).filter_by(livestock_id=animal, name=name).first():
            source = "https://adc.go.ke/goats-and-sheep/" if name in {"Galla", "Red Maasai"} else "https://kalroerepository.kalro.org/bitstreams/8d6f3ef8-7be0-4a84-b613-f6b15f0cee0d/download"
            db.add(LivestockBreed(livestock_id=animal, name=name, risk_attributes=risks,
                adapted_regions=regions, source_url=source, source_checked_on=CHECKED))
    for name, address, county_name in VENDORS:
        county = _by_name(db, County, county_name)
        if county and not db.query(Vendor).filter_by(name=name, address=address).first():
            db.add(Vendor(name=name, county_id=county, address=address,
                source_url=VMD_RETAILERS, source_checked_on=CHECKED))
    # Public shop listing gives current displayed prices but does not expose
    # inventory quantity; stock intentionally remains unknown.
    uasin_gishu = _by_name(db, County, "Uasin Gishu")
    if uasin_gishu:
        mavuno = db.query(Vendor).filter_by(name="MavunoVet", address="Kaptagat Road, Eldoret").first()
        if mavuno:
            mavuno.contact_phone = "0712-607-412"
            mavuno.contact_email = "info@mavunovet.co.ke"
            mavuno.opening_hours = "Monday-Saturday 08:00-18:00"
            mavuno.source_url = "https://mavunovet.co.ke/shop.html"
            mavuno.source_checked_on = CHECKED
            sungura = db.query(CropVariety).filter_by(name="Sungura 301").first()
            for item, price in (("SC Sungura 301 Hybrid Maize Seed 2kg", 1490), ("Bharati 54 Hybrid Maize Seeds", 850)):
                if not db.query(VendorProduct).filter_by(vendor_id=mavuno.id, product_name=item).first():
                    db.add(VendorProduct(vendor_id=mavuno.id, crop_variety_id=sungura.id if "Sungura" in item and sungura else None,
                        product_name=item, price_kes=price, unit="2 kg pack", price_checked_on=CHECKED,
                        source_url="https://mavunovet.co.ke/shop.html"))
    for name, county_name, sub_county, ward, lat, lon, source in MARKETS:
        county = _by_name(db, County, county_name)
        if county and not db.query(Market).filter_by(county_id=county, name=name).first():
            market_days = "All week long" if name == "Wakulima Market" else None
            db.add(Market(county_id=county, name=name, sub_county=sub_county, ward=ward,
                latitude=lat, longitude=lon, market_days=market_days, source_url=source, source_checked_on=CHECKED))
    db.commit()
