from app.ai.gemini_service import GeminiService

service = GeminiService()

response = service.generate_recommendation(
   context = {
    "farmer": {
        "name": "John Doe",
        "county": "Meru",
        "farm_size": 2.5,
        "experience": "Intermediate"
    },

    "current_crops": [
        "Beans"
    ],

    "current_livestock": [
        "Dairy Goats"
    ],

    "weather": {
        "temperature": 22,
        "humidity": 74,
        "rainfall": 145,
        "forecast": "Rain expected in 3 days"
    },

    "earth_engine": {
        "soil_moisture": 0.63,
        "ndvi": 0.78,
        "land_cover": "Cropland"
    },

    "market": {
        "maize_price": 4200,
        "beans_price": 9600
    }
}
)

print(response)