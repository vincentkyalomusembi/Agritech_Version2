import app.models
from app.database.sessions import SessionLocal
from app.farmers.repository import FarmerRepository
from app.recommendations.ai_services.livestock_recommendation_service import (
    LivestockRecommendationService,
)


db = SessionLocal()

try:
    farmer_repository = FarmerRepository(db)
    farmers = farmer_repository.list_all()

    if not farmers:
        print("NO FARMERS FOUND")
        raise SystemExit

    farmer = farmers[0]

    print(f"Testing farmer: {farmer.full_name}")
    print(f"Farmer ID: {farmer.id}")
    print("\nGenerating livestock recommendation...\n")

    service = LivestockRecommendationService(
        db=db,
        provider="gemini",
    )

    recommendation = service.recommend(
        farmer.id
    )

    print("=== LIVESTOCK RECOMMENDATION ===")
    print(recommendation)

finally:
    db.close()