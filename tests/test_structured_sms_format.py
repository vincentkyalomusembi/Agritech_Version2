from app.recommendations.structured_service import StructuredRecommendationService as S, format_recommendation_sms


def test_requested_crop_matching():
    assert S._requested_name("crop", {"crop_name": "beans"}) == "beans"
    assert S._requested_name("livestock", {"livestock_type": "Other"}) is None
    assert S._same_name("beans", "Beans")
    assert S._same_name("Goats", "Goats")
    assert not S._same_name("beans", "Maize")


def test_sms_is_one_clean_message():
    card = {
        "primary": {"crop": "Beans", "name": "Nyota (KAD 02)", "maturity_days_min": 60, "maturity_days_max": 90},
        "why_fit": "Drought tolerant and early maturing, suited to dry Meru conditions. Extra text.",
        "actions": ["Confirm seed label and local rainfall before planting."],
        "alternatives": [{"name": "Angaza (KMR 11)"}],
        "vendors": [{"name": "Inputs Today", "price_kes": 1490.0, "unit": "2 kg pack", "phone": "0712607412"}],
    }
    out = format_recommendation_sms(card)
    assert len(out) == 1 and len(out[0]) <= 300
    assert "Beans - Nyota" in out[0] and "Inputs Today" in out[0] and "(1/" not in out[0]
    print(out[0])


def test_sms_without_vendor_or_catalogue_match():
    card = {"primary": {"crop": "Maize", "name": "DH04"}, "requested": "cassava", "requested_unavailable": True,
            "why_fit": "x", "actions": [], "alternatives": [], "vendors": []}
    text = format_recommendation_sms(card)[0]
    assert "No verified cassava" in text and "agrovet" in text
