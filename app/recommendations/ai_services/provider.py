from abc import ABC, abstractmethod

from app.core.config import settings


class AIProvider(ABC):
    """
    Common interface for AI recommendation providers.

    Gemini and OpenAI must implement the same method so the rest
    of the recommendation system does not depend on one provider.
    """

    @abstractmethod
    def generate_recommendation(
        self,
        context: dict,
        recommendation_type: str,
    ) -> str:
        """
        Generate a recommendation from the supplied context.
        """
        raise NotImplementedError


class GeminiProvider(AIProvider):
    """
    Gemini implementation of the recommendation provider.
    """

    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("Gemini API key is not configured.")

        from google import genai

        self.client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

    def generate_recommendation(
        self,
        context: dict,
        recommendation_type: str,
    ) -> str:

        prompt = build_recommendation_prompt(
            context,
            recommendation_type,
        )

        response = self.client.models.generate_content(
            model="gemini-3.7-flash",
            contents=prompt,
        )

        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")

        return response.text.strip()


class OpenAIProvider(AIProvider):
    """
    OpenAI implementation of the recommendation provider.
    """

    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OpenAI API key is not configured.")

        from openai import OpenAI

        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY
        )

    def generate_recommendation(
        self,
        context: dict,
        recommendation_type: str,
    ) -> str:

        prompt = build_recommendation_prompt(
            context,
            recommendation_type,
        )

        response = self.client.responses.create(
            model="gpt-5.6-luna",
            input=prompt,
        )

        if not response.output_text:
            raise RuntimeError("OpenAI returned an empty response.")

        return response.output_text.strip()


def build_recommendation_prompt(
    context: dict,
    recommendation_type: str,
) -> str:
    """
    Build one compact prompt shared by Gemini and OpenAI.

    The context comes from our application services, not from the AI.
    """

    return f"""
You are an agricultural advisory AI for Kenyan farmers.

Give a practical {recommendation_type} recommendation using ONLY
the farmer context provided below.

IMPORTANT RULES:

1. Be specific.
   Never give a generic recommendation such as "grow maize".
   If recommending a crop, give a suitable VARIETY.
   If recommending livestock, give a suitable BREED.

2. Explain WHY the variety or breed fits this farmer.
   Consider county, weather, forecast, soil, farm size, experience,
   environmental conditions and market information where available.

3. Prefer Kenyan agricultural knowledge and organizations.
   When appropriate, identify a relevant Kenyan organization such as
   KALRO or another legitimate agricultural institution.

4. Never invent:
   - organizations
   - suppliers
   - prices
   - product availability
   - disease resistance claims
   - guaranteed yields

5. Keep the answer short and suitable for SMS.

6. Use simple English that a Kenyan farmer can easily understand.

7. Prioritize actionable information.

Return exactly this structure:

RECOMMENDATION:
[Specific crop + variety OR livestock + breed]

WHY:
[Short reason why it fits]

SOURCE:
[Relevant Kenyan organization/source, if confidently known]

ACTION:
[One or two practical next steps]

SMS:
[Very short farmer-friendly message, maximum about 320 characters]

FARMER CONTEXT:
{context}
""".strip()


def get_ai_provider(provider: str = "gemini") -> AIProvider:
    """
    Return the configured AI provider.

    Gemini is the default provider.
    """

    provider = provider.lower().strip()

    if provider == "gemini":
        return GeminiProvider()

    if provider == "openai":
        return OpenAIProvider()

    raise ValueError(
        f"Unsupported AI provider: {provider}"
    )