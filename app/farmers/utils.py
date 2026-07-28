def normalize_phone_number(phone_number: str) -> str:
    """Normalize Kenyan MSISDNs to the +254 format used for farmer identity."""

    # ---- Copilot Improvement ----
    # Keep phone canonicalization in a small shared utility so REST, SMS and
    # USSD flows cannot drift into querying different farmer identities.
    # ---- End Improvement ----
    cleaned = phone_number.strip().replace(" ", "")
    if cleaned.startswith("+"):
        return cleaned
    if cleaned.startswith("254"):
        return f"+{cleaned}"
    if cleaned.startswith("0"):
        return f"+254{cleaned[1:]}"
    return cleaned
