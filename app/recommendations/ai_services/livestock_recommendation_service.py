from uuid import UUID

from sqlalchemy.orm import Session

from app.recommendations.context_service import RecommendationContextService
from app.recommendations.ai_services.provider import get_ai_provider


class LivestockRecommendationService:
    """
    Handles livestock recommendations.

    This service:
    1. Builds the farmer context.
    2. Sends the context to the selected AI provider.
    3. Returns the AI recommendation.

    Persistence and SMS delivery are handled later.
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
        Generate a livestock recommendation for a farmer.
        """

        # Build the farmer's complete agricultural context.
        context = self.context_service.build_context(
            farmer_id
        )

        # Ask the AI provider for a specific livestock breed.
        recommendation = self.ai_provider.generate_recommendation(
            context=context,
            recommendation_type="livestock",
        )

        return recommendation.strip()