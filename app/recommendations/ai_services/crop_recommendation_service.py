
from uuid import UUID

from sqlalchemy.orm import Session

from app.recommendations.context_service import RecommendationContextService
from app.recommendations.ai_services.provider import get_ai_provider
from app.recommendations.model import Recommendation, RecommendationType
from app.recommendations.repository import RecommendationRepository


class CropRecommendationService:
    """Generate and save crop recommendations."""

    def __init__(self, db: Session, provider: str = "gemini"):
        self.context_service = RecommendationContextService(db)
        self.ai_provider = get_ai_provider(provider)
        self.repository = RecommendationRepository(db)
        self.provider_name = provider

    def recommend(self, farmer_id: UUID) -> str:
        # Build context using the farmer's real data.
        context = self.context_service.build_context(farmer_id)

        # Generate a specific crop variety recommendation.
        result = self.ai_provider.generate_recommendation(
            context=context,
            recommendation_type="crop",
        ).strip()

        # Extract the title from the recommendation.
        lines = result.splitlines()
        title = "Crop recommendation"

        for i, line in enumerate(lines):
            if line.strip().upper() == "RECOMMENDATION:":
                if i + 1 < len(lines):
                    title = lines[i + 1].strip()
                break
            elif line.strip().upper().startswith("RECOMMENDATION:"):
                title = line.split(":", 1)[1].strip()
                break

        # Save the result before returning it.
        saved = Recommendation(
            farmer_id=farmer_id,
            recommendation_type=RecommendationType.CROP,
            title=title[:200],
            recommendation_text=result,
            ai_provider=self.provider_name,
            is_sent=False,
        )
        self.repository.create(saved)

        return result
