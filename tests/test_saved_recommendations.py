
from app.database.sessions import SessionLocal
from app.recommendations.repository import RecommendationRepository
from app.farmers.repository import FarmerRepository

db = SessionLocal()

try:
    # Find the test farmer
    farmer = FarmerRepository(db).get_by_phone(
        "+254792246733"
    )

    if not farmer:
        print("Farmer not found. Check the test farmer's phone number.")
    else:
        repository = RecommendationRepository(db)
        records = repository.get_by_farmer(farmer.id, limit=5)

        for record in records:
            print("\nTitle:", record.title)
            print("Type:", record.recommendation_type.value)
            print("AI provider:", record.ai_provider)
            print("Sent:", record.is_sent)

finally:
    db.close()
