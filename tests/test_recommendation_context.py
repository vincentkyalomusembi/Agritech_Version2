from app.database.sessions import SessionLocal
from app.farmers.repository import FarmerRepository
from app.recommendations.context_service import RecommendationContextService


db = SessionLocal()

try:
    # Get an existing farmer from the database
    farmer_repository = FarmerRepository(db)
    farmers = farmer_repository.list_all()

    if not farmers:
        print("NO FARMERS FOUND")
        raise SystemExit

    farmer = farmers[0]

    print(f"Testing farmer: {farmer.full_name}")
    print(f"Farmer ID: {farmer.id}")

    # Build recommendation context
    service = RecommendationContextService(db)
    context = service.build_context(farmer.id)

    print("\n=== RECOMMENDATION CONTEXT ===")
    print(context)

    print("\n=== CONTEXT TEST PASSED ===")

finally:
    db.close()