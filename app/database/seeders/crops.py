from app.crops.model import Crop

CROPS = [
    "Maize",
    "Beans",
    "Rice",
    "Wheat",
    "Sorghum",
    "Millet",
    "Potatoes",
    "Sweet Potatoes",
    "Cassava",
    "Bananas",
    "Tomatoes",
    "Onions",
    "Cabbage",
    "Kale",
    "Spinach",
    "Carrots",
    "Capsicum",
    "French Beans",
    "Peas",
    "Coffee",
    "Tea",
    "Avocado",
    "Mango",
    "Watermelon",
    "Pawpaw",
    "Sugarcane",
    "Cotton",
    "Sunflower",
    "Groundnuts",
    "Soybeans",
]


def seed_crops(db):
    for crop_name in CROPS:

        exists = (
            db.query(Crop)
            .filter(Crop.name == crop_name)
            .first()
        )

        if not exists:
            db.add(Crop(name=crop_name))

    db.commit()

    print(" Crops seeded successfully.")