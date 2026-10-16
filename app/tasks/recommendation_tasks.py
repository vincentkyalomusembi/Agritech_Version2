"""
Celery tasks for async AI recommendation generation.
Fan-out: fetch all data in parallel, then call AI, then send SMS.
"""
import json
import logging
from datetime import datetime
from uuid import UUID

from celery import shared_task

from app.core.celery_app import celery_app
from app.core.africas_talking import AfricasTalkingClient
from app.database.sessions import SessionLocal
from app.sms_sessions.repository import SMSSessionRepository
from app.sms_sessions.service import SMSSessionService

logger = logging.getLogger(__name__)


def _get_db_and_session(session_id: str):
    db = SessionLocal()
    repo = SMSSessionRepository(db)
    svc = SMSSessionService(db)
    session = db.query(__import__("app.sms_sessions.model", fromlist=["SMSSession"]).SMSSession).filter_by(id=session_id).first()
    return db, repo, svc, session


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_crop_recommendation(self, session_id: str, farmer_id: str, phone: str):
    db = SessionLocal()
    try:
        from app.recommendations.structured_service import StructuredRecommendationService, format_recommendation_sms
        from app.recommendations.repository import RecommendationRepository
        from app.recommendations.sms_service import RecommendationSMSService
        from app.sms_sessions.model import SMSSession

        session = db.query(SMSSession).filter_by(id=session_id).first()
        if not session:
            return

        svc = SMSSessionService(db)
        data = svc.get_data(session)
        card = StructuredRecommendationService(db).recommend(UUID(farmer_id), "crop", data)
        recommendation = RecommendationRepository(db).get_by_id(UUID(card["id"]))

        svc.complete_session(session)
        sms_service = RecommendationSMSService(db)
        for segment in format_recommendation_sms(card):
            outcome = sms_service.send_message(recommendation, phone, segment)
            if outcome.get("status") == "error":
                logger.error("Crop recommendation SMS submission failed: %s", outcome.get("reason"))
    except Exception as exc:
        db.rollback()
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _send_failure_sms(phone, "Crop Recommendation")
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_livestock_recommendation(self, session_id: str, farmer_id: str, phone: str):
    db = SessionLocal()
    try:
        from app.recommendations.structured_service import StructuredRecommendationService, format_recommendation_sms
        from app.recommendations.repository import RecommendationRepository
        from app.recommendations.sms_service import RecommendationSMSService
        from app.sms_sessions.model import SMSSession

        session = db.query(SMSSession).filter_by(id=session_id).first()
        if not session:
            return

        svc = SMSSessionService(db)
        data = svc.get_data(session)
        card = StructuredRecommendationService(db).recommend(UUID(farmer_id), "livestock", data)
        recommendation = RecommendationRepository(db).get_by_id(UUID(card["id"]))

        svc.complete_session(session)
        sms_service = RecommendationSMSService(db)
        for segment in format_recommendation_sms(card):
            outcome = sms_service.send_message(recommendation, phone, segment)
            if outcome.get("status") == "error":
                logger.error("Livestock recommendation SMS submission failed: %s", outcome.get("reason"))
    except Exception as exc:
        db.rollback()
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _send_failure_sms(phone, "Livestock Recommendation")
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_weather_alerts(self, session_id: str, farmer_id: str, phone: str):
    db = SessionLocal()
    try:
        from app.farmers.repository import FarmerRepository
        from app.farmers.location import farmer_coordinates
        from app.integrations.openweather.client import OpenWeatherClient
        from app.integrations.google_earth_engine.service import EarthEngineService
        from app.ai.gemini_service import GeminiService
        from app.sms_sessions.model import SMSSession

        session = db.query(SMSSession).filter_by(id=session_id).first()
        svc = SMSSessionService(db)
        farmer = FarmerRepository(db).get_by_id(farmer_id)

        latitude, longitude, _ = farmer_coordinates(farmer)
        weather = OpenWeatherClient().get_weather_summary(latitude, longitude)
        observations = None
        try:
            observations = EarthEngineService().get_environment(latitude, longitude)
        except Exception:
            logger.exception("GEE observations unavailable for weather alert farmer_id=%s", farmer.id)
        tip = _safe_fetch(lambda: GeminiService().generate_recommendation({
            "farmer": {"county": farmer.county.name},
            "weather": weather,
            "satellite_observations": observations,
            "request": "Give a 1-sentence farming tip based on this weather.",
        }))

        current = weather.get("current", {})
        forecast_periods = weather.get("forecast", {}).get("periods", [])
        tomorrow = next(
            (period for period in forecast_periods if (period.get("time") or "")[:10] != datetime.utcnow().strftime("%Y-%m-%d")),
            forecast_periods[0] if forecast_periods else {},
        )

        msg = (
            f"Weather Alert for {farmer.county.name}:\n"
            f"Now: {current.get('weather','N/A')}, {current.get('temperature','?')}C\n"
            f"Forecast {tomorrow.get('time','')}: {tomorrow.get('weather','N/A')}, "
            f"{tomorrow.get('temperature','?')}C, rain {tomorrow.get('rainfall_mm', 0)}mm/3h\n"
        )
        ndvi = (observations or {}).get("ndvi") or {}
        if ndvi.get("available"):
            msg += f"Satellite NDVI {ndvi.get('ndvi')} ({ndvi.get('image_date')}; MODIS observation).\n"
        rainfall = (observations or {}).get("rainfall") or {}
        if rainfall.get("available"):
            msg += (
                f"Observed CHIRPS rain {rainfall.get('rainfall_mm')}mm over "
                f"{rainfall.get('coverage_days')} available days, through {rainfall.get('data_through_date')}.\n"
            )
        if tip:
            msg += f"Tip: {tip}\n"
        msg += "Reply MENU to return."

        if session:
            svc.complete_session(session)
        AfricasTalkingClient().send_sms(phone, msg)
    except Exception as exc:
        db.rollback()
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _send_failure_sms(phone, "Weather Alerts")
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_market_prices(self, session_id: str, farmer_id: str, phone: str):
    db = SessionLocal()
    try:
        from app.farmers.repository import FarmerRepository
        from app.farmers.location import farmer_coordinates
        from app.farmer_crops.repository import FarmerCropRepository
        from app.market_prices.repository import MarketPriceRepository
        from app.sms_sessions.model import SMSSession
        import datetime

        session = db.query(SMSSession).filter_by(id=session_id).first()
        svc = SMSSessionService(db)
        farmer = FarmerRepository(db).get_by_id(farmer_id)
        crops = FarmerCropRepository(db).get_farmer_crops(farmer_id)
        market_repo = MarketPriceRepository(db)

        lines = [f"Market Prices ({datetime.date.today()}):"]
        for fc in crops:
            price = market_repo.get_latest_by_crop(fc.crop_id)
            if price:
                stale = " (cached)" if (datetime.date.today() - price.price_date).days > 1 else ""
                lines.append(f"{fc.crop.name}: KES {price.average_price}/{price.unit}{stale}")
        if len(lines) == 1:
            lines.append("No market data available for your crops.")
        lines.append("Reply MENU to return.")

        if session:
            svc.complete_session(session)
        AfricasTalkingClient().send_sms(phone, "\n".join(lines))
    except Exception as exc:
        db.rollback()
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _send_failure_sms(phone, "Market Prices")
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_disease_alert(self, session_id: str, farmer_id: str, phone: str):
    db = SessionLocal()
    try:
        from app.farmers.repository import FarmerRepository
        from app.integrations.openweather.client import OpenWeatherClient
        from app.integrations.google_earth_engine.service import EarthEngineService
        from app.integrations.google_earth_engine.cache_service import EnvironmentalCacheService
        from app.ai.gemini_service import GeminiService
        from app.sms_sessions.model import SMSSession

        session = db.query(SMSSession).filter_by(id=session_id).first()
        if not session:
            return

        svc = SMSSessionService(db)
        farmer = FarmerRepository(db).get_by_id(farmer_id)
        data = svc.get_data(session)

        latitude, longitude, _ = farmer_coordinates(farmer)
        weather = _safe_fetch(lambda: OpenWeatherClient().get_weather_summary(
            latitude, longitude
        ))
        cached_earth = EnvironmentalCacheService(db).get_for_farmer(farmer)
        earth = cached_earth or _safe_fetch(lambda: EarthEngineService().get_environment(
            latitude, longitude
        ))

        context = {
            "farmer": {"name": farmer.full_name, "county": farmer.county.name},
            "session_inputs": data,
            "weather": weather,
            "earth_engine": earth,
            "request": "Assess disease risk and provide action steps.",
        }

        recommendation = _safe_fetch(lambda: GeminiService().generate_recommendation(context))
        if not recommendation:
            recommendation = "Monitor crops/livestock closely. Contact a local extension officer if symptoms worsen."

        svc.complete_session(session)
        AfricasTalkingClient().send_sms(
            phone,
            f"Disease Alert for {farmer.full_name}:\n{recommendation}\nReply MENU to return.",
        )
    except Exception as exc:
        db.rollback()
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _send_failure_sms(phone, "Disease Alerts")
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_expert_request(self, session_id: str, farmer_id: str, phone: str):
    db = SessionLocal()
    try:
        from app.expert_requests.schema import ExpertRequestCreate
        from app.expert_requests.services.expert_request_service import ExpertRequestService
        from app.sms_sessions.model import SMSSession

        session = db.query(SMSSession).filter_by(id=session_id).first()
        if not session:
            return

        svc = SMSSessionService(db)
        data = svc.get_data(session)
        issue_type = data.get("issue_type", "Crop")
        ExpertRequestService(db).create_request(ExpertRequestCreate(
            farmer_id=UUID(farmer_id), issue_type=issue_type,
            description=data.get("description", ""),
        ), source_session_id=UUID(session_id))
        svc.complete_session(session)
    except Exception as exc:
        db.rollback()
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _send_failure_sms(phone, "Expert Request")
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_profile_update(self, session_id: str, farmer_id: str, phone: str):
    db = SessionLocal()
    try:
        from app.farmers.repository import FarmerRepository
        from app.counties.repository import CountyRepository
        from app.crops.model import Crop
        from app.livestock.model import Livestock
        from app.farmer_crops.model import FarmerCrop
        from app.farmer_livestocks.model import FarmerLivestock
        from app.sms_sessions.model import SMSSession

        session = db.query(SMSSession).filter_by(id=session_id).first()
        if not session:
            return

        svc = SMSSessionService(db)
        farmer_repo = FarmerRepository(db)
        farmer = farmer_repo.get_by_id(farmer_id)
        data = svc.get_data(session)
        action = data.get("action", "")
        new_value = data.get("new_value", "").strip()

        if action == "name":
            farmer.full_name = new_value
            farmer_repo.update(farmer)
            msg = f"Name updated to {new_value}."
        elif action == "county":
            county = CountyRepository(db).get_by_name_fuzzy(new_value)
            if county:
                farmer.county_id = county.id
                farmer.sub_county = None
                farmer.ward = None
                farmer.constituency_id = None
                farmer.ward_id = None
                farmer.latitude = None
                farmer.longitude = None
                farmer_repo.update(farmer)
                msg = f"County updated to {county.name}. Local area and coordinates cleared; update your ward if needed."
            else:
                msg = f"County '{new_value}' not found. No changes made."
        elif action == "sub_county_ward":
            parts = [part.strip() for part in new_value.split(",", 1)]
            if len(parts) != 2 or not all(parts):
                msg = "Please provide both sub-county and ward separated by a comma. No changes made."
            else:
                from app.counties.model import Constituency, Ward
                constituency = db.query(Constituency).filter(
                    Constituency.county_id == farmer.county_id,
                    Constituency.name.ilike(parts[0]),
                ).first()
                ward = db.query(Ward).filter(
                    Ward.constituency_id == constituency.id,
                    Ward.name.ilike(parts[1]),
                ).first() if constituency else None
                if constituency is None or ward is None:
                    msg = "That ward was not found in the selected constituency. No changes made."
                else:
                    farmer.sub_county, farmer.ward = constituency.name, ward.name
                    farmer.constituency_id, farmer.ward_id = constituency.id, ward.id
                    farmer_repo.update(farmer)
                    msg = f"Location updated: {constituency.name}, {ward.name}."
        elif action == "add_crop":
            crop = db.query(Crop).filter(Crop.name.ilike(new_value)).first()
            if crop:
                exists = db.query(FarmerCrop).filter_by(farmer_id=farmer.id, crop_id=crop.id).first()
                if exists:
                    msg = f"{crop.name} is already on your profile."
                else:
                    fc = FarmerCrop(
                        farmer_id=farmer.id,
                        crop_id=crop.id,
                        farm_size=float(data["farm_size"]),
                        soil_type=data["soil_type"],
                        experience_level=data["experience_level"],
                    )
                    db.add(fc)
                    db.commit()
                    msg = f"{crop.name} added to your profile ({fc.farm_size:g} acres)."
            else:
                msg = f"Crop '{new_value}' not found in our database."
        elif action == "add_livestock":
            ls = db.query(Livestock).filter(Livestock.name.ilike(new_value)).first()
            if ls:
                exists = db.query(FarmerLivestock).filter_by(farmer_id=farmer.id, livestock_id=ls.id).first()
                if exists:
                    msg = f"{ls.name} is already on your profile."
                else:
                    fl = FarmerLivestock(farmer_id=farmer.id, livestock_id=ls.id, herd_size=int(data["herd_size"]))
                    db.add(fl)
                    db.commit()
                    msg = f"{ls.name} added to your profile ({fl.herd_size} animals)."
            else:
                msg = f"Livestock '{new_value}' not found in our database."
        else:
            msg = "No changes made."

        svc.complete_session(session)
        AfricasTalkingClient().send_sms(phone, f"{msg}\nReply MENU to return.")
    except Exception as exc:
        db.rollback()
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            _send_failure_sms(phone, "Profile Update")
    finally:
        db.close()


@celery_app.task
def scrape_market_prices():
    """Daily market price scrape — runs via Celery beat."""
    db = SessionLocal()
    try:
        from app.market_prices.service import MarketPriceService
        MarketPriceService(db).scrape_and_store()
    finally:
        db.close()


# ── Helpers ───────────────────────────────────────────────────────────

def _safe_fetch(fn):
    try:
        return fn()
    except Exception:
        return None


def _send_failure_sms(phone: str, service: str) -> None:
    AfricasTalkingClient().send_sms(
        phone,
        f"Sorry, we could not complete your {service} request. Please try again. Dial *384#.",
    )


def _rule_based_crop_fallback(data: dict, weather: dict | None, market: list) -> str:
    crop = data.get("crop_name", "your crop")
    lines = [f"Recommendation for {crop}:"]
    if weather:
        temp = weather.get("current", {}).get("temperature")
        if temp:
            lines.append(f"Current temp: {temp}C. Ensure adequate irrigation.")
    if market:
        p = market[0]
        lines.append(f"Market price: KES {p['price_kes']}/{p['unit']} ({p['date']}).")
    lines.append("Consult your local extension officer for detailed advice.")
    return " ".join(lines)
