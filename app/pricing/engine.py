"""Pure farm-size quoting rules. No I/O — safe to unit test."""

from __future__ import annotations

from typing import Any

SIZE_CLASSES = ("Micro", "Small", "Medium", "Large")
CLASS_RANK = {name: index for index, name in enumerate(SIZE_CLASSES)}
AMOUNT_CAP_KES = 70  # Large farms never pay more than KSh 70 / month

PLAN_ALIASES = {
    "Basic": "Micro",
    "Standard": "Small",
    "Premium": "Medium",
    "Micro": "Micro",
    "Small": "Small",
    "Medium": "Medium",
    "Large": "Large",
}

DEFAULT_TLU_WEIGHTS = {
    "cattle": 1.0,
    "goats": 0.15,
    "sheep": 0.15,
    "chicken": 0.01,
    "ducks": 0.01,
    "turkeys": 0.01,
    "poultry": 0.01,
    "other": 0.2,
}

DEFAULT_BANDS = (
    {"name": "Micro", "min_acres": 0.0, "max_acres": 1.0, "min_tlu": 0.0, "max_tlu": 1.0, "kes": 0},
    {"name": "Small", "min_acres": 1.0, "max_acres": 3.0, "min_tlu": 1.0, "max_tlu": 5.0, "kes": 20},
    {"name": "Medium", "min_acres": 3.0, "max_acres": 10.0, "min_tlu": 5.0, "max_tlu": 20.0, "kes": 40},
    {"name": "Large", "min_acres": 10.0, "max_acres": None, "min_tlu": 20.0, "max_tlu": None, "kes": 70},
)

PAID_SERVICES = {
    "crop_recommendation",
    "livestock_recommendation",
    "disease_alerts",
    "expert_request",
}

DEFAULT_ENTITLEMENTS = {
    "Micro": ["weather_alerts", "market_prices", "profile_update", "subscription"],
    "Small": [
        "weather_alerts",
        "market_prices",
        "profile_update",
        "subscription",
        "crop_recommendation",
        "livestock_recommendation",
        "disease_alerts",
        "expert_request",
    ],
    "Medium": [
        "weather_alerts",
        "market_prices",
        "profile_update",
        "subscription",
        "crop_recommendation",
        "livestock_recommendation",
        "disease_alerts",
        "expert_request",
    ],
    "Large": [
        "weather_alerts",
        "market_prices",
        "profile_update",
        "subscription",
        "crop_recommendation",
        "livestock_recommendation",
        "disease_alerts",
        "expert_request",
    ],
}


def normalize_plan_name(plan_name: str | None) -> str:
    """Map legacy Basic/Standard/Premium names onto size classes."""

    if not plan_name:
        return "Micro"
    return PLAN_ALIASES.get(plan_name, plan_name if plan_name in CLASS_RANK else "Micro")


def livestock_weight(species_name: str, weights: dict[str, float] | None = None) -> float:
    table = weights or DEFAULT_TLU_WEIGHTS
    key = species_name.strip().lower()
    if key in table:
        return float(table[key])
    if "chicken" in key or "duck" in key or "turkey" in key or "poultry" in key:
        return float(table.get("poultry", 0.01))
    return float(table.get("other", 0.2))


def classify_value(value: float, min_key: str, max_key: str, bands: tuple | list = DEFAULT_BANDS) -> str:
    for band in bands:
        lower = float(band[min_key])
        upper = band[max_key]
        if value < lower:
            continue
        if upper is None or value < float(upper):
            return str(band["name"])
    return "Large"


def max_class(*classes: str) -> str:
    chosen = "Micro"
    for name in classes:
        if CLASS_RANK.get(name, 0) > CLASS_RANK.get(chosen, 0):
            chosen = name
    return chosen


def amount_for_class(size_class: str, bands: tuple | list = DEFAULT_BANDS) -> int:
    for band in bands:
        if band["name"] == size_class:
            return min(int(band["kes"]), AMOUNT_CAP_KES)
    return 0


def compute_from_inputs(
    acres: float,
    herd_by_species: dict[str, int],
    *,
    weights: dict[str, float] | None = None,
    bands: tuple | list = DEFAULT_BANDS,
) -> dict[str, Any]:
    """Quote a size class from acres + named herd counts."""

    safe_acres = max(0.0, float(acres or 0.0))
    tlu_by_species: dict[str, float] = {}
    tlu_total = 0.0
    for species, count in herd_by_species.items():
        head = max(0, int(count or 0))
        units = round(head * livestock_weight(species, weights), 4)
        tlu_by_species[species] = units
        tlu_total += units

    crop_class = classify_value(safe_acres, "min_acres", "max_acres", bands)
    livestock_class = classify_value(tlu_total, "min_tlu", "max_tlu", bands)
    size_class = max_class(crop_class, livestock_class)
    monthly_kes = amount_for_class(size_class, bands)
    has_size_input = safe_acres > 0 or tlu_total > 0

    return {
        "acres": round(safe_acres, 4),
        "tlu_by_species": tlu_by_species,
        "tlu_total": round(tlu_total, 4),
        "crop_class": crop_class,
        "livestock_class": livestock_class,
        "size_class": size_class,
        "monthly_kes": monthly_kes,
        "has_size_input": has_size_input,
    }


def format_quote_sms(
    size_class: str,
    acres: float,
    herd_by_species: dict[str, int],
    monthly_kes: int,
) -> str:
    herd_bits = [
        f"{count} {name.lower()}"
        for name, count in herd_by_species.items()
        if count
    ]
    herd_text = ", ".join(herd_bits) if herd_bits else "no livestock"
    return (
        f"Your farm size: {size_class} ({acres:.1f} acres, {herd_text}). "
        f"Monthly: KES {monthly_kes}. Reply 1 to pay, 2 to cancel."
    )
