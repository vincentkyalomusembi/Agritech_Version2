# ── Welcome ──────────────────────────────────────────────────────────
WELCOME = (
    "CON Welcome to AgriTech AI\n"
    "1. Register\n"
    "2. Login\n"
    "3. About"
)

ABOUT = (
    "END AgriTech AI helps Kenyan farmers with crop, livestock, "
    "weather & market guidance. Powered by AI. Dial *384# to start."
)

# ── Registration ──────────────────────────────────────────────────────
REG_NAME = "CON Enter your full name:"
REG_ID = "CON Enter your National ID number:"
REG_COUNTY = "CON Enter your county name (e.g. Nairobi, Kisumu, Nakuru):"
REG_PIN = "CON Create a 4-digit PIN:"
REG_PIN_CONFIRM = "CON Confirm your 4-digit PIN:"
REG_SUCCESS = "END Registration successful! Check your SMS for details."
REG_PIN_MISMATCH = "END PINs do not match. Please dial again to register."
REG_PHONE_EXISTS = "END This phone number is already registered. Dial *384# to login."
REG_ID_EXISTS = "END This National ID is already registered. Dial *384# to login."
REG_COUNTY_NOT_FOUND = "END County not found. Please dial again and enter a valid county name."

# ── Login ─────────────────────────────────────────────────────────────
LOGIN_PIN = "CON Enter your 4-digit PIN:"
LOGIN_FAILED = "END Incorrect PIN. Please try again."
NOT_REGISTERED = "END Phone not registered. Select 1 to register."

# ── Main Menu ─────────────────────────────────────────────────────────
MAIN_MENU = (
    "CON Welcome back, {name}\n"
    "1. Crop Recommendations\n"
    "2. Livestock Recommendations\n"
    "3. Weather Alerts\n"
    "4. Disease Alerts\n"
    "5. Market Prices\n"
    "6. Request Expert\n"
    "7. My Profile\n"
    "8. Subscribe\n"
    "0. Exit"
)

# ── Service launch confirmations (all END — USSD stops here) ──────────
CROP_CONFIRMATION = "END Your Crop Recommendation session has started. Continue via SMS."
LIVESTOCK_CONFIRMATION = "END Your Livestock Recommendation session has started. Continue via SMS."
WEATHER_CONFIRMATION = "END Fetching weather for your county. Check your SMS shortly."
DISEASE_CONFIRMATION = "END Your Disease Alert session has started. Continue via SMS."
MARKET_CONFIRMATION = "END Fetching market prices for your crops. Check your SMS shortly."
EXPERT_CONFIRMATION = "END Your Expert Request session has started. Continue via SMS."
PROFILE_CONFIRMATION = "END Your Profile session has started. Continue via SMS."
SUBSCRIBE_CONFIRMATION = "END Your Subscription session has started. Continue via SMS."

SESSION_ACTIVE = "END You have an active {service} session. Reply STOP via SMS to cancel, then dial again."

GOODBYE = "END Thank you for using AgriTech AI. Goodbye."
INVALID_OPTION = "END Invalid option. Please dial *384# and try again."

MENU_OPTIONS = {
    "1": "crop_recommendation",
    "2": "livestock_recommendation",
    "3": "weather_alerts",
    "4": "disease_alerts",
    "5": "market_prices",
    "6": "expert_request",
    "7": "profile_update",
    "8": "subscription",
}

SERVICE_LABELS = {
    "crop_recommendation": "Crop Recommendation",
    "livestock_recommendation": "Livestock Recommendation",
    "weather_alerts": "Weather Alerts",
    "disease_alerts": "Disease Alerts",
    "market_prices": "Market Prices",
    "expert_request": "Expert Request",
    "profile_update": "Profile",
    "subscription": "Subscription",
}

SERVICE_CONFIRMATIONS = {
    "crop_recommendation": CROP_CONFIRMATION,
    "livestock_recommendation": LIVESTOCK_CONFIRMATION,
    "weather_alerts": WEATHER_CONFIRMATION,
    "disease_alerts": DISEASE_CONFIRMATION,
    "market_prices": MARKET_CONFIRMATION,
    "expert_request": EXPERT_CONFIRMATION,
    "profile_update": PROFILE_CONFIRMATION,
    "subscription": SUBSCRIBE_CONFIRMATION,
}
