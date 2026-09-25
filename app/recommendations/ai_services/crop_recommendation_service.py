from uuid import UUID

from sqlalchemy.orm import Session

from app.recommendations.context_service import RecommendationContextService
from app.recommendations.ai_services.provider import get_ai_provider


class CropRecommendationService:
    """
    Handles crop recommendations.

    This service:
    1. Builds the farmer context.
    2. Sends the context to the selected AI provider.
    3. Returns the AI recommendation.

    It does not save the recommendation yet.
    Persistence comes in Phase 3.5.
    """

    def __init__(
        self,
        db: Session,
        provider: str = "gemini",
    ):
        self.context_service = RecommendationContextService(db)
        self.ai_provider = get_ai_provider(provider)

    def recommend(
        self,
        farmer_id: UUID,
    ) -> str:
        """
        Generate a crop recommendation for a farmer.
        """

        # Build the complete farmer context first.
        context = self.context_service.build_context(
            farmer_id
        )

        # Ask the AI provider to generate a specific crop
        # variety recommendation.
        recommendation = self.ai_provider.generate_recommendation(
            context=context,
            recommendation_type="crop",
        )

        return recommendation.strip()