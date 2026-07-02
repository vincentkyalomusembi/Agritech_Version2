import random

from faker import Faker
from sqlalchemy.orm import Session

from app.counties.model import County
from app.experts.model import Expert, ExpertType

fake = Faker()


# Kenyan Names


FIRST_NAMES = [
    "John", "James", "Peter", "David", "Kevin",
    "Brian", "Victor", "Dennis", "Samuel", "Daniel",
    "Mary", "Grace", "Faith", "Mercy", "Lilian",
    "Susan", "Jane", "Joyce", "Esther", "Beatrice",
    "Joseph", "Michael", "Paul", "Charles", "Daniel",
    "Alice", "Rose", "Dorcas", "Lucy", "Carol"
]

LAST_NAMES = [
    "Mwangi", "Kamau", "Kariuki", "Maina", "Njoroge",
    "Kimani", "Mutua", "Musyoka", "Mutiso", "Nzomo",
    "Otieno", "Odhiambo", "Achieng", "Ouma", "Okoth",
    "Kiptoo", "Kiprotich", "Cheruiyot", "Chebet", "Koech",
    "Barasa", "Wekesa", "Simiyu", "Wafula", "Namwamba",
    "Muriuki", "Kathure", "M'Mbijiwe", "Nyambura", "Wanjiru"
]


def generate_kenyan_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"



# Phone Numbers


phone_counter = 700000001


def generate_phone():
    global phone_counter
    phone = f"+254{phone_counter}"
    phone_counter += 1
    return phone



# Seeder


def seed_experts(db: Session):

    if db.query(Expert).count() > 0:
        print(" Experts already seeded")
        return

    counties = db.query(County).all()

    experts = []

    for county in counties:

        agriculture_officer = Expert(
            full_name=generate_kenyan_name(),
            phone_number=generate_phone(),
            expert_type=ExpertType.AGRICULTURE,
            county_id=county.id,
            organization=f"{county.name} County Agriculture Office",
            is_available=True,
        )

        veterinary_officer = Expert(
            full_name=generate_kenyan_name(),
            phone_number=generate_phone(),
            expert_type=ExpertType.VETERINARY,
            county_id=county.id,
            organization=f"{county.name} County Veterinary Office",
            is_available=True,
        )

        experts.append(agriculture_officer)
        experts.append(veterinary_officer)

    db.add_all(experts)
    db.commit()

    print(f" Seeded {len(experts)} experts successfully.")