import app.models
from app.database.sessions import SessionLocal

from app.database.seeders.counties import seed_counties
from app.database.seeders.crops import seed_crops
from app.database.seeders.livestock import seed_livestock
from app.database.seeders.experts import seed_experts


def seed_database():
    db = SessionLocal()

    try:
        print("=" * 60)
        print(" Starting database seeding...")
        print("=" * 60)

        print("\n1. Seeding Counties...")
        seed_counties(db)

        print("\n2. Seeding Crops...")
        seed_crops(db)

        print("\n3. Seeding Livestock...")
        seed_livestock(db)

        print("\n4. Seeding Experts...")
        seed_experts(db)

        print("\n" + "=" * 60)
        print(" Database seeding completed successfully!")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"\n Error: {e}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()