import json
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.ai.llm import LLMRouter
from app.catalogue.model import CropVariety, LivestockBreed
from app.catalogue.model import VendorProduct
from app.farmers.repository import FarmerRepository
from app.recommendations.context_service import RecommendationContextService
from app.recommendations.model import Recommendation, RecommendationType
from app.recommendations.repository import RecommendationRepository
from app.recommendations.vendor_matching import VendorMatchingService


class StructuredRecommendationService:
    def __init__(self, db: Session, ai=None):
        self.db = db
        self.ai = ai
        self.farmers = FarmerRepository(db)
        self.context_service = RecommendationContextService(db)

    def recommend(self, farmer_id: UUID, kind: str, session_inputs: dict | None = None) -> dict:
        farmer = self.farmers.get_by_id(farmer_id)
        if farmer is None:
            raise ValueError("Farmer not found")
        environment_context = self.context_service.environmental_context(farmer)
        latitude, longitude = environment_context["latitude"], environment_context["longitude"]
        weather, environment = environment_context["weather_forecast"], environment_context["observations"]

        livestock = kind == "livestock"
        model = LivestockBreed if livestock else CropVariety
        parent = model.livestock if livestock else model.crop
        rows = self.db.query(model).options(joinedload(parent)).order_by(model.name.asc()).all()
        candidates = []
        for row in rows:
            item = {
                "id": str(row.id), "name": row.name,
                "altitude_min_m": row.altitude_min_m, "altitude_max_m": row.altitude_max_m,
                "rainfall_min_mm": row.rainfall_min_mm, "rainfall_max_mm": row.rainfall_max_mm,
                "maturity_days_min": row.maturity_days_min, "maturity_days_max": row.maturity_days_max,
                "risk_attributes": row.risk_attributes, "adapted_regions": row.adapted_regions,
            }
            if livestock:
                item["livestock"] = row.livestock.name
            else:
                item["crop"] = row.crop.name
            candidates.append(item)
        if not candidates:
            raise ValueError("No sourced catalogue entries are available")
        eligible_primary_ids = {
            str(value) for (value,) in self.db.query(
                VendorProduct.livestock_breed_id if livestock else VendorProduct.crop_variety_id
            ).filter(
                (VendorProduct.livestock_breed_id if livestock else VendorProduct.crop_variety_id).is_not(None)
            ).distinct().all()
        }
        if not eligible_primary_ids:
            raise ValueError("No catalogue entry has a verified vendor product listing")

        context = {
            "kind": kind,
            "farmer": {"name": farmer.full_name, "county": farmer.county.name,
                       "latitude": latitude, "longitude": longitude,
                       "sub_county": farmer.sub_county, "ward": farmer.ward},
            "session_inputs": session_inputs or {},
            "weather_forecast": weather,
            "rainfall_and_ndvi_observations": environment,
            "catalogue_only_choices": candidates,
            "primary_must_be_in_these_vendor_listed_ids": sorted(eligible_primary_ids),
            "vendor_stock_is_not_ai_input": True,
        }
        try:
            provider_client = self.ai or LLMRouter()
            selection = provider_client.generate_structured_recommendation(context)
            result = self._validate_selection(selection, candidates, eligible_primary_ids)
            provider = getattr(provider_client, "last_provider", None) or "gemini"
        except Exception:
            result = self._fallback(candidates, farmer.county.name, weather, environment, eligible_primary_ids)
            provider = "catalogue_fallback"

        by_id = {item["id"]: item for item in candidates}
        primary = by_id[result["primary_id"]]
        alternatives = [by_id[item_id] for item_id in result["alternative_ids"]]
        vendors = [] if livestock else VendorMatchingService(self.db).match_variety(UUID(primary["id"]), farmer)
        card = {
            "kind": kind,
            "primary": primary,
            "why_fit": result["why_fit"],
            "evidence": {"weather_forecast": weather, "rainfall_and_ndvi": environment},
            "alternatives": alternatives,
            "planting_window": result.get("planting_window"),
            "spacing": result.get("spacing"),
            "actions": result.get("actions", [])[:4],
            "vendors": vendors,
            "vendor_note": (
                "Vendor location is not verified; call to confirm distance, price, and stock."
                if vendors and vendors[0].get("distance_km") is None
                else None if vendors else "No matching product listing is available yet."
            ),
        }
        recommendation = Recommendation(
            farmer_id=farmer.id,
            crop_variety_id=UUID(primary["id"]) if not livestock else None,
            livestock_breed_id=UUID(primary["id"]) if livestock else None,
            vendor_product_id=UUID(vendors[0]["product_id"]) if vendors else None,
            recommendation_type=RecommendationType.LIVESTOCK if livestock else RecommendationType.CROP,
            title=f"{primary.get('crop') or primary.get('livestock')}: {primary['name']}"[:200],
            recommendation_text=json.dumps(card, ensure_ascii=False),
            recommendation_data=card,
            ai_provider=provider,
            is_sent=False,
        )
        RecommendationRepository(self.db).create(recommendation)
        return {"id": str(recommendation.id), **card}

    @staticmethod
    def _validate_selection(selection: dict, candidates: list[dict], eligible_primary_ids: set[str]) -> dict:
        ids = {item["id"] for item in candidates}
        primary = str(selection["primary_id"])
        if primary not in ids or primary not in eligible_primary_ids:
            raise ValueError("AI selected an item outside the vendor-listed catalogue")
        alternatives = []
        for value in selection.get("alternative_ids", []):
            candidate_id = str(value)
            if candidate_id in ids and candidate_id != primary and candidate_id not in alternatives:
                alternatives.append(candidate_id)
            if len(alternatives) == 2:
                break
        if len(alternatives) < 2:
            primary_item = next(item for item in candidates if item["id"] == primary)
            ordered = [item for item in candidates if item["id"] != primary]
            ordered.sort(key=lambda item: item.get("crop", item.get("livestock")) == primary_item.get("crop", primary_item.get("livestock")))
            for item in ordered:
                if item["id"] == primary or item["id"] in alternatives:
                    continue
                alternatives.append(item["id"])
                if len(alternatives) == 2:
                    break
        # Catalogue facts do not currently include planting windows or spacing.
        # Keep those fields empty rather than trusting unsupported generated text.
        return {"primary_id": primary, "alternative_ids": alternatives,
                "why_fit": str(selection.get("why_fit") or "Selected from the verified local catalogue.")[:500],
                "planting_window": None, "spacing": None,
                "actions": [str(v)[:200] for v in selection.get("actions", [])[:4]]}

    @staticmethod
    def _fallback(candidates: list[dict], county: str, weather, environment, eligible_primary_ids: set[str]) -> dict:
        def score(item):
            regions = (item.get("adapted_regions") or "").lower()
            value = 5 if county.lower() in regions else 0
            dry = str((environment or {}).get("rainfall", "")).lower()
            forecast = str((weather or {}).get("forecast", "")).lower()
            if any(term in dry + forecast for term in ("low", "dry", "drought")) and "drought" in (item.get("risk_attributes") or "").lower():
                value += 3
            return value
        ranked = sorted((item for item in candidates if item["id"] in eligible_primary_ids), key=score, reverse=True)
        primary = ranked[0]
        alternatives = [candidate for candidate in ranked[1:] if candidate.get("crop", candidate.get("livestock")) != primary.get("crop", primary.get("livestock"))]
        alternatives.extend(candidate for candidate in ranked[1:] if candidate not in alternatives)
        alt_ids = [candidate["id"] for candidate in alternatives[:2]]
        return {"primary_id": primary["id"], "alternative_ids": alt_ids,
                "why_fit": f"{primary['name']} is in the sourced catalogue for Kenya. Confirm local rainfall and seed availability before planting.",
                "planting_window": None, "spacing": None,
                "actions": ["Use the package label and local extension advice for planting date and spacing."]}


def format_recommendation_sms(card: dict, max_chars: int = 160) -> list[str]:
    primary = card["primary"]
    name = f"{primary.get('crop') or primary.get('livestock')} {primary['name']}"
    vendors = card.get("vendors") or []
    price = f" KES {vendors[0]['price_kes']}/{vendors[0]['unit']} at {vendors[0]['name']}" if vendors and vendors[0].get("price_kes") is not None else ""
    other = ", ".join(f"{entry.get('crop') or entry.get('livestock')} {entry['name']}" for entry in card.get("alternatives", []))
    planting = card.get("planting_window") or "check local planting rains"
    spacing = card.get("spacing") or "follow seed label"
    messages = [f"Try {name}. {card.get('why_fit','')}".strip(),
                f"Alternatives: {other or 'none verified'}. Plant: {planting}; spacing: {spacing}.",
                f"Where to buy:{price or ' no matching priced stock listing yet.'}"]
    segments = []
    for message in messages:
        while message:
            cut = min(max_chars, len(message))
            if cut < len(message) and " " in message[:cut]:
                cut = message.rfind(" ", 0, cut)
            if cut == 0:
                cut = min(max_chars, len(message))
            segments.append(message[:cut].strip())
            message = message[cut:].strip()
    if len(segments) > 1:
        count = len(segments)
        segments = [f"({i}/{count}) {part}"[:max_chars] for i, part in enumerate(segments, 1)]
    return segments
