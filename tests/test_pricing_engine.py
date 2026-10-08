from app.pricing.engine import compute_from_inputs, format_quote_sms, normalize_plan_name


def test_half_acre_is_micro_free():
    result = compute_from_inputs(0.5, {})
    assert result["size_class"] == "Micro"
    assert result["monthly_kes"] == 0
    assert result["crop_class"] == "Micro"


def test_two_acres_is_small():
    result = compute_from_inputs(2.0, {})
    assert result["size_class"] == "Small"
    assert result["monthly_kes"] == 20


def test_two_acres_plus_forty_cattle_is_large_capped():
    result = compute_from_inputs(2.0, {"Cattle": 40})
    assert result["livestock_class"] == "Large"
    assert result["size_class"] == "Large"
    assert result["monthly_kes"] == 70


def test_two_hundred_poultry_is_not_large():
    result = compute_from_inputs(0.0, {"Chicken": 200})
    assert result["tlu_total"] == 2.0
    assert result["size_class"] == "Small"
    assert result["monthly_kes"] == 20


def test_two_thousand_acres_still_capped_at_70():
    result = compute_from_inputs(2000.0, {})
    assert result["size_class"] == "Large"
    assert result["monthly_kes"] == 70


def test_mixed_one_acre_three_goats_is_small_not_summed():
    result = compute_from_inputs(1.0, {"Goats": 3})
    assert result["crop_class"] == "Small"
    assert result["livestock_class"] == "Micro"
    assert result["size_class"] == "Small"
    assert result["monthly_kes"] == 20


def test_legacy_plan_aliases():
    assert normalize_plan_name("Basic") == "Micro"
    assert normalize_plan_name("Standard") == "Small"
    assert normalize_plan_name("Premium") == "Medium"


def test_quote_sms_is_two_lines_of_plain_kes():
    text = format_quote_sms("Small", 2.0, {"Goats": 4}, 20)
    assert "Small" in text
    assert "KES 20" in text
    assert "4 goats" in text
