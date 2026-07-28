from google import genai

from app.ai.prompts import SYSTEM_PROMPT
from app.core.config import settings


class GeminiService:
    """
    Handles communication with Gemini.
    """

    def __init__(self):
        # ---- Copilot Improvement ----
        # Fail before constructing an SDK client with an empty credential so
        # configuration faults are clear and do not trigger avoidable retries.
        # ---- End Improvement ----
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("Gemini API is not configured.")
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

        # ---- Copilot Improvement ----
        # Ask for a bounded, structured answer and trim overlong provider text
        # so USSD/SMS follow-up messages remain concise and predictable.
        # ---- End Improvement ----
        prompt = f"""
{SYSTEM_PROMPT}

Farmer Data

{context}

Return at most six short bullet points covering crop varieties, livestock,
disease risks, fertilizer/feed, farming action, and market opportunity. Omit
categories not supported by the supplied data.
"""

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        return (response.text or "").strip()[:1200]
