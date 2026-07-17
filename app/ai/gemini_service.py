from google import genai

from app.ai.prompts import SYSTEM_PROMPT
from app.core.config import settings


class GeminiService:
    """
    Handles communication with Gemini.
    """

    def __init__(self):
        self.client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

    def generate_recommendation(
        self,
        context: dict,
    ) -> str:
        """
        Generate an agricultural recommendation.
        """

        prompt = f"""
{SYSTEM_PROMPT}

Farmer Data

{context}
"""

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        return response.text