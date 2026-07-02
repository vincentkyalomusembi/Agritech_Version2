"""
Import every SQLAlchemy model here.

Alembic imports this file so it can discover
all database tables.
"""

# Example later
from app.counties.model import County
from app.crops.model import Crop
from app.livestock.model import Livestock
from app.farmers.model import Farmer
from app.farmer_crops.model import FarmerCrop
from app.farmer_livestocks.model import FarmerLivestock
from app.subscriptions.model import Subscription
from app.experts.model import Expert
from app.expert_requests.model import ExpertRequest
from app.products.model import AgriculturalProduct
from app.market_prices.model import MarketPrice
from app.recommendations.model import Recommendation
from app.notifications.model import Notification
from app.sms_sessions.model import SMSSession
from app.advisory.model import Advisory