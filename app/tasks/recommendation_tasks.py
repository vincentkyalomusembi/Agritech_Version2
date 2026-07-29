"""
Celery tasks for async AI recommendation generation.
Fan-out: fetch all data in parallel, then call AI, then send SMS.
"""
import json

from celery import shared_task

from app.core.celery_app import celery_app
from app.core.africas_talking import AfricasTalkingClient
from app.database.sessions import SessionLocal
from app.sms_sessions.repository import SMSSessionRepository
from app.sms_sessions.service import SMSSessionService


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
        from app.farmers.repository import FarmerRepository
        from app.farmer_crops.repository import FarmerCropRepository
        from app.integrations.openweather.client import OpenWeatherClient
        from app.integrations.google_earth_engine.service import EarthEngineService
        from app.market_prices.repository import MarketPriceRepository
        from app.ai.gemini_service import GeminiService
        from app.sms_sessions.model import SMSSession

        session = db.query(SMSSession).filter_by(id=session_id).first()
        if not session:
            return

        svc = SMSSessionService(db)
        farmer = FarmerRepository(db).get_by_id(farmer_id)
        data = svc.get_data(session)

        weather = _safe_fetch(lambda: OpenWeatherClient().get_weather_summary(
            farmer.county.latitude, farmer.county.longitude
        ))
        earth = _safe_fetch(lambda: EarthEngineService().get_environment(
            farmer.county.latitude, farmer.county.longitude
        ))
        crops = FarmerCropRepository(db).get_farmer_crops(farmer_id)
        market_repo = MarketPriceRepository(db)
        market_data = []
        for fc in crops:
            price = market_repo.get_latest_by_crop(fc.crop_id)
            if price:
                market_data.append({"crop": fc.crop.name, "price_kes": price.average_price, "unit": price.unit, "date": str(price.price_date)})

        context = {
            "farmer": {"name": farmer.full_name, "county": farmer.county.name},
            "session_inputs": data,
            "weather": weather,
            "earth_engine": earth,
            "market_prices": market_data,
        }

        recommendation = _safe_fetch(lambda: GeminiService().generate_recommendation(context))
        if not recommendation:
            recommendation = _rule_based_crop_fallback(data, weather, market_data)

        svc.complete_session(session)
        AfricasTalkingClient().send_sms(
            phone,
            f"Crop Recommendation for {farmer.full_name}:\n{recommendation}\nReply MENU to return.",
        )
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
        from app.farmers.repository import FarmerRepository
        from app.farmer_livestocks.repository import FarmerLivestockRepository
        from app.integrations.openweather.client import OpenWeatherClient
        from app.integrations.google_earth_engine.service import EarthEngineService
        from app.ai.gemini_service import GeminiService
        from app.sms_sessions.model import SMSSession

        session = db.query(SMSSession).filter_by(id=session_id).first()
        if not session:
            return

        svc = SMSSessionService(db)
        farmer = FarmerRepository(db).get_by_id(farmer_id)
        data = svc.get_data(session)

        weather = _safe_fetch(lambda: OpenWeatherClient().get_weather_summary(
            farmer.county.latitude, farmer.county.longitude
        ))
        earth = _safe_fetch(lambda: EarthEngineService().get_environment(
            farmer.county.latitude, farmer.county.longitude
        ))
        livestock = FarmerLivestockRepository(db).get_farmer_livestock(farmer_id)

        context = {
            "farmer": {"name": farmer.full_name, "county": farmer.county.name},
            "session_inputs": data,
            "registered_livestock": [{"type": fl.livestock.name, "herd_size": fl.herd_size} for fl in livestock],
            "weather": weather,
            "earth_engine": earth,
        }

        recommendation = _safe_fetch(lambda: GeminiService().generate_recommendation(context))
        if not recommendation:
            recommendation = "Ensure adequate water and feed. Monitor for disease signs. Consult a vet if needed."

        svc.complete_session(session)
        AfricasTalkingClient().send_sms(
            phone,
            f"Livestock Recommendation for {farmer.full_name}:\n{recommendation}\nReply MENU to return.",
        )
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
        from app.integrations.openweather.client import OpenWeatherClient
        from app.ai.gemini_service import GeminiService
        from app.sms_sessions.model import SMSSession

        session = db.query(SMSSession).filter_by(id=session_id).first()
        svc = SMSSessionService(db)
        farmer = FarmerRepository(db).get_by_id(farmer_id)

        weather = OpenWeatherClient().get_weather_summary(
            farmer.county.latitude, farmer.county.longitude
        )
        tip = _safe_fetch(lambda: GeminiService().generate_recommendation({
            "farmer": {"county": farmer.county.name},
            "weather": weather,
            "request": "Give a 1-sentence farming tip based on this weather.",
        }))

        current = weather.get("current", {})
        forecast_periods = weather.get("forecast", {}).get("periods", [])
        tomorrow = forecast_periods[0] if forecast_periods else {}

        msg = (
            f"Weather Alert for {farmer.county.name}:\n"
            f"Now: {current.get('weather','N/A')}, {current.get('temperature','?')}C\n"
            f"Tomorrow: {tomorrow.get('weather','N/A')}, {tomorrow.get('temperature','?')}C\n"
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
        from app.ai.gemini_service import GeminiService
        from app.sms_sessions.model import SMSSession

        session = db.query(SMSSession).filter_by(id=session_id).first()
        if not session:
            return

        svc = SMSSessionService(db)
        farmer = FarmerRepository(db).get_by_id(farmer_id)
        data = svc.get_data(session)

        weather = _safe_fetch(lambda: OpenWeatherClient().get_weather_summary(
            farmer.county.latitude, farmer.county.longitude
        ))
        earth = _safe_fetch(lambda: EarthEngineService().get_environment(
            farmer.county.latitude, farmer.county.longitude
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
        from app.farmers.repository import FarmerRepository
        from app.experts.repository import ExpertRepository
        from app.experts.model import ExpertType
        from app.expert_requests.model import ExpertRequest
        from app.sms_sessions.model import SMSSession

        session = db.query(SMSSession).filter_by(id=session_id).first()
        if not session:
            return

        svc = SMSSessionService(db)
        farmer = FarmerRepository(db).get_by_id(farmer_id)
        data = svc.get_data(session)

        issue_type = data.get("issue_type", "Crop")
        expert_type = ExpertType.VETERINARY if issue_type == "Livestock" else ExpertType.AGRICULTURE

        expert = ExpertRepository(db).list_filtered(
            county_id=farmer.county_id,
            expert_type=expert_type,
            is_available=True,
            limit=1,
        )
        expert = expert[0] if expert else None

        if expert:
            request = ExpertRequest(
                farmer_id=farmer.id,
                expert_id=expert.id,
                issue_type=issue_type,
                description=data.get("description", ""),
            )
            db.add(request)
            db.commit()

            AfricasTalkingClient().send_sms(
                phone,
                f"Expert request received.\n{expert.full_name} will contact you ({data.get('availability','')}).\nContact: {expert.phone_number}\nReply MENU to return.",
            )
            AfricasTalkingClient().send_sms(
                expert.phone_number,
                f"New request from {farmer.full_name}, {farmer.county.name}.\nIssue: {data.get('description','')}\nContact: {phone}\nTime: {data.get('availability','')}",
            )
        else:
            AfricasTalkingClient().send_sms(
                phone,
                f"No available expert in {farmer.county.name} right now. We will notify you when one is available.\nReply MENU to return.",
            )

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
                farmer_repo.update(farmer)
                msg = f"County updated to {county.name}."
            else:
                msg = f"County '{new_value}' not found. No changes made."
        elif action == "add_crop":
            crop = db.query(Crop).filter(Crop.name.ilike(new_value)).first()
            if crop:
                fc = FarmerCrop(farmer_id=farmer.id, crop_id=crop.id, farm_size=1.0, soil_type="Not specified", experience_level="Beginner")
                db.add(fc)
                db.commit()
                msg = f"Crop {crop.name} added to your profile."
            else:
                msg = f"Crop '{new_value}' not found in our database."
        elif action == "add_livestock":
            ls = db.query(Livestock).filter(Livestock.name.ilike(new_value)).first()
            if ls:
                fl = FarmerLivestock(farmer_id=farmer.id, livestock_id=ls.id, herd_size=1)
                db.add(fl)
                db.commit()
                msg = f"Livestock {ls.name} added to your profile."
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
