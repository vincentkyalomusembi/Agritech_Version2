"""
SMS conversation flow definitions.

Each flow is a list of steps. Each step has:
  - key:      the dict key stored in session_data
  - question: the SMS text sent to the farmer
  - choices:  optional dict of valid reply → stored value (None = free text)
"""

CROP_FLOW = [
    {
        "key": "crop_name",
        "question": "Hi {name}, let's find the best crop for you.\nWhat crop are you planning to grow? Reply with the crop name.",
        "choices": None,
    },
    {
        "key": "farm_size",
        "question": "What is your farm size? Example: 2 acres",
        "choices": None,
    },
    {
        "key": "soil_type",
        "question": "What is your soil type?\n1. Loam\n2. Clay\n3. Sandy\n4. Not sure",
        "choices": {"1": "Loam", "2": "Clay", "3": "Sandy", "4": "Not sure"},
    },
    {
        "key": "experience_level",
        "question": "What is your farming experience?\n1. Beginner\n2. Intermediate\n3. Expert",
        "choices": {"1": "Beginner", "2": "Intermediate", "3": "Expert"},
    },
]

LIVESTOCK_FLOW = [
    {
        "key": "livestock_type",
        "question": "Hi {name}, let's help with your livestock.\nWhat livestock do you keep or plan to keep?\n1. Cattle\n2. Goats\n3. Sheep\n4. Poultry\n5. Other",
        "choices": {"1": "Cattle", "2": "Goats", "3": "Sheep", "4": "Poultry", "5": "Other"},
    },
    {
        "key": "herd_size",
        "question": "How many animals do you have or plan to have?",
        "choices": None,
    },
    {
        "key": "primary_goal",
        "question": "What is your primary goal?\n1. Milk\n2. Meat\n3. Eggs\n4. Breeding",
        "choices": {"1": "Milk", "2": "Meat", "3": "Eggs", "4": "Breeding"},
    },
    {
        "key": "has_vet",
        "question": "Do you have access to a veterinarian?\n1. Yes\n2. No",
        "choices": {"1": "Yes", "2": "No"},
    },
]

DISEASE_FLOW = [
    {
        "key": "concern",
        "question": "Hi {name}, let's check for disease risks.\nWhich crop or livestock are you concerned about?",
        "choices": None,
    },
    {
        "key": "has_symptoms",
        "question": "Have you noticed any symptoms?\n1. Yes\n2. No",
        "choices": {"1": "Yes", "2": "No"},
    },
    {
        "key": "symptom_description",
        "question": "Describe the symptom briefly.\nExample: Yellow leaves, limping animal",
        "choices": None,
        "condition_key": "has_symptoms",
        "condition_value": "Yes",
    },
]

EXPERT_FLOW = [
    {
        "key": "issue_type",
        "question": "Hi {name}, let's connect you with an expert.\nWhat do you need help with?\n1. Crop\n2. Livestock\n3. Soil\n4. Business",
        "choices": {"1": "Crop", "2": "Livestock", "3": "Soil", "4": "Business"},
    },
    {
        "key": "description",
        "question": "Briefly describe your issue. (Reply with a short description)",
        "choices": None,
    },
    {
        "key": "availability",
        "question": "When are you available?\n1. Morning\n2. Afternoon\n3. Evening",
        "choices": {"1": "Morning", "2": "Afternoon", "3": "Evening"},
    },
]

PROFILE_FLOW = [
    {
        "key": "action",
        "question": "Hi {name}, choose a profile option:\n1. Change name\n2. Change county\n3. Add crop\n4. Add livestock\n5. View profile\n6. Choose constituency/sub-county and ward",
        "choices": {"1": "name", "2": "county", "3": "add_crop", "4": "add_livestock", "5": "view", "6": "sub_county_ward"},
    },
    # Step 1 branches — handled dynamically in the SMS handler
    {
        "key": "new_value",
        "question": "",  # set dynamically based on action
        "choices": None,
    },
    {"key": "farm_size", "question": "How many acres do you grow this crop on? Enter a number, for example 2.", "choices": None, "condition_action": "add_crop"},
    {"key": "soil_type", "question": "What is the soil type?\n1. Loam\n2. Clay\n3. Sandy\n4. Not sure", "choices": {"1": "Loam", "2": "Clay", "3": "Sandy", "4": "Not sure"}, "condition_action": "add_crop"},
    {"key": "experience_level", "question": "Your experience with this crop?\n1. Beginner\n2. Intermediate\n3. Experienced", "choices": {"1": "Beginner", "2": "Intermediate", "3": "Experienced"}, "condition_action": "add_crop"},
    {"key": "herd_size", "question": "How many animals do you have? Enter a whole number.", "choices": None, "condition_action": "add_livestock"},
]

SUBSCRIPTION_FLOW = [
    {
        "key": "confirmed",
        "question": (
            "Hi {name}, reply 1 to pay the quoted monthly amount or 2 to cancel."
        ),
        "choices": {"1": "Yes", "2": "No"},
    },
]

# Legacy aliases kept so older SMS sessions and activate_subscription() still resolve.
PLAN_PRICES = {
    "Basic": 0,
    "Standard": 20,
    "Premium": 40,
    "Micro": 0,
    "Small": 20,
    "Medium": 40,
    "Large": 70,
}

# Services that need no questions — fire-and-forget
NO_QUESTION_SERVICES = {"weather_alerts", "market_prices"}

FLOWS = {
    "crop_recommendation": CROP_FLOW,
    "livestock_recommendation": LIVESTOCK_FLOW,
    "disease_alerts": DISEASE_FLOW,
    "expert_request": EXPERT_FLOW,
    "profile_update": PROFILE_FLOW,
    "subscription": SUBSCRIPTION_FLOW,
}


def format_question(step: dict, *, name: str = "", plan: str = "") -> str:
    """Render a flow prompt with a clear reply mode for basic-phone users."""
    question = step.get("question", "").format(name=name, plan=plan).strip()
    if not question:
        return question
    instruction = (
        "Reply with the number only."
        if step.get("choices")
        else "Reply by typing your answer."
    )
    if instruction.lower() in question.lower():
        return question
    return f"{question}\n{instruction}"
