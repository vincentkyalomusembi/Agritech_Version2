
from unittest.mock import Mock

from app.recommendations.sms_service import RecommendationSMSService


# Create the service without connecting to the database or SMS provider.
service = RecommendationSMSService.__new__(RecommendationSMSService)

service.db = Mock()
service.recommendations = Mock()
service.farmers = Mock()
service.sms_client = Mock()

# Prepare a saved recommendation and a farmer.
recommendation = Mock()
recommendation.id = "test-recommendation"
recommendation.farmer_id = "test-farmer"
recommendation.is_sent = False
recommendation.recommendation_text = """
RECOMMENDATION:
Suitable goat breed

SMS:
Ask your livestock officer about suitable goat breeds.
"""

farmer = Mock()
farmer.phone_number = "+254700000000"

service.recommendations.get_by_id.return_value = recommendation
service.farmers.get_by_id.return_value = farmer

# Simulate a successful provider response.
service.sms_client.send_sms.return_value = {
    "SMSMessageData": {
        "Message": "Sent to 1/1",
        "Recipients": [{"status": "Success"}],
    }
}

result = service.send_recommendation(recommendation.id)

print("Result:", result["status"])
print("SMS sent to provider:", service.sms_client.send_sms.called)
print("Recommendation marked as sent:", recommendation.is_sent)

assert result["status"] == "submitted"
assert service.sms_client.send_sms.called
assert recommendation.is_sent is True

# Test duplicate-send protection.
service.sms_client.send_sms.reset_mock()
result = service.send_recommendation(recommendation.id)

assert result["status"] == "skipped"
assert not service.sms_client.send_sms.called

print("SMS service tests passed.")
