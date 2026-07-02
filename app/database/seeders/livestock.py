from app.livestock.model import Livestock

LIVESTOCK = [
    "Cattle",
    "Goats",
    "Sheep",
    "Chicken",
    "Ducks",
    "Turkeys",
    "Pigs",
    "Rabbits",
    "Camels",
    "Fish",
    "Bees",
    "Donkeys",
]

def seed_livestock(db):
    for livestock_name in LIVESTOCK:

        exists = (
            db.query(Livestock)
            .filter(Livestock.name == livestock_name)
            .first()
        )

        if not exists:
            db.add(Livestock(name=livestock_name))

    db.commit()

    print("Livestock seeded successfully.")