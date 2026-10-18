"""
Spread AI calls across Gemini and OpenAI.

Requests alternate between the configured providers so neither carries the
whole load, and a failing provider falls through to the next one.
"""
import itertools
import logging
import time

from app.ai.gemini_service import GeminiService
from app.ai.openai_service import OpenAIService
from app.core.config import settings

logger = logging.getLogger(__name__)

_PROVIDERS = (("gemini", GeminiService, "GEMINI_API_KEY"), ("openai", OpenAIService, "OPENAI_API_KEY"))
_turn = itertools.count()

# A provider that fails is skipped for a while instead of slowing every other
# request. Auth/quota problems need human action, so they cool down longer.
_cooldown_until: dict[str, float] = {}
QUOTA_COOLDOWN_SECONDS = 600
ERROR_COOLDOWN_SECONDS = 60


def _cooldown_for(exc: Exception) -> int:
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    text = str(exc).lower()
    if status in (401, 403, 429) or "quota" in text or "credit" in text or "api key" in text:
        return QUOTA_COOLDOWN_SECONDS
    return ERROR_COOLDOWN_SECONDS


class LLMRouter:
    def __init__(self):
        self.last_provider: str | None = None

    def _ordered(self):
        configured = [(name, cls) for name, cls, key in _PROVIDERS if getattr(settings, key)]
        if not configured:
            raise RuntimeError("No AI provider is configured.")
        now = time.monotonic()
        healthy = [item for item in configured if _cooldown_until.get(item[0], 0) <= now]
        # If every provider is cooling down, still try them rather than fail outright.
        available = healthy or configured
        start = next(_turn) % len(available)
        return available[start:] + available[:start]

    def _call(self, method: str, context: dict):
        error = None
        for name, cls in self._ordered():
            try:
                result = getattr(cls(), method)(context)
                self.last_provider = name
                _cooldown_until.pop(name, None)
                return result
            except Exception as exc:
                cooldown = _cooldown_for(exc)
                _cooldown_until[name] = time.monotonic() + cooldown
                logger.warning("%s %s failed; skipping it for %ss: %s", name, method, cooldown, exc)
                error = exc
        raise error

    def generate_recommendation(self, context: dict) -> str:
        return self._call("generate_recommendation", context)

    def generate_structured_recommendation(self, context: dict) -> dict:
        return self._call("generate_structured_recommendation", context)
