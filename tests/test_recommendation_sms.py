
from app.recommendations.sms_service import RecommendationSMSService

sample = """
RECOMMENDATION:
Livestock: Galla Goat

WHY:
Suitable for dry conditions.

SOURCE:
KALRO

ACTION:
Consult your local livestock officer.

SMS:
For Baringo's dry climate, ask your livestock officer about suitable goat breeds.
"""

message = RecommendationSMSService.extract_sms(sample)

print("Extracted SMS:")
print(message)

assert message.startswith("For Baringo")
assert "RECOMMENDATION:" not in message
assert "WHY:" not in message

print("\nSMS extraction passed.")
