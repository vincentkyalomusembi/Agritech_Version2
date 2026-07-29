"""
Celery tasks for M-Pesa subscription payments.
"""
import datetime

from app.core.celery_app import celery_app
from app.core.africas_talking import AfricasTalkingClient
from app.database.sessions import SessionLocal


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def initiate_mpesa_stk_push(self, session_id: str, farmer_id: str, phone: str, plan: str, amount: int):
    """Initiate STK push. Subscription is activated via the Daraja callback."""
    db = SessionLocal()
    try:
        from app.integrations.mpesa.client import MpesaClient
        from app.farmers.repository import FarmerRepository

        farmer = FarmerRepository(db).get_by_id(farmer_id)
        result = MpesaClient().stk_push(
            phone=phone,
            amount=amount,
            account_ref=f"AGRI-{farmer.national_id}",
            description=f"AgriTech AI {plan} subscription",
        )
        checkout_id = result.get("CheckoutRequestID", "")

        # Store checkout ID in session data for callback matching
        from app.sms_sessions.model import SMSSession
        from app.sms_sessions.service import SMSSessionService
        import json

        session = db.query(SMSSession).filter_by(id=session_id).first()
        if session:
            data = json.loads(session.session_data) if session.session_data else {}
            data["checkout_request_id"] = checkout_id
            data["plan"] = plan
            data["amount"] = amount
            session.session_data = json.dumps(data)
            db.commit()

    except Exception as exc:
        db.rollback()
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            AfricasTalkingClient().send_sms(
                phone,
                "Payment request failed. Please try again. Dial *384# to subscribe.",
            )
            from app.sms_sessions.model import SMSSession
            from app.sms_sessions.service import SMSSessionService
            session = db.query(SMSSession).filter_by(id=session_id).first()
            if session:
                SMSSessionService(db).mark_failed(session)
    finally:
        db.close()


@celery_app.task
def activate_free_subscription(session_id: str, farmer_id: str, phone: str, plan: str):
    """Activate a free (Basic) subscription immediately."""
    db = SessionLocal()
    try:
        _activate_subscription(db, farmer_id, plan)
        from app.sms_sessions.model import SMSSession
        from app.sms_sessions.service import SMSSessionService
        session = db.query(SMSSession).filter_by(id=session_id).first()
        if session:
            SMSSessionService(db).complete_session(session)
        from app.farmers.repository import FarmerRepository
        farmer = FarmerRepository(db).get_by_id(farmer_id)
        AfricasTalkingClient().send_sms(
            phone,
            f"Subscription confirmed.\nPlan: {plan}\nThank you, {farmer.full_name}!\nReply MENU to return.",
        )
    finally:
        db.close()


@celery_app.task
def handle_mpesa_callback(checkout_request_id: str, result_code: int, result_desc: str):
    """
    Called by the Daraja callback route after payment confirmation.
    result_code 0 = success.
    """
    db = SessionLocal()
    try:
        from app.sms_sessions.model import SMSSession
        from app.sms_sessions.service import SMSSessionService
        import json

        # Find session by checkout_request_id stored in session_data
        sessions = db.query(SMSSession).filter(
            SMSSession.session_data.contains(checkout_request_id)
        ).all()

        for session in sessions:
            svc = SMSSessionService(db)
            data = json.loads(session.session_data) if session.session_data else {}
            phone = session.farmer.phone_number
            plan = data.get("plan", "Standard")

            if result_code == 0:
                _activate_subscription(db, str(session.farmer_id), plan)
                svc.complete_session(session)
                AfricasTalkingClient().send_sms(
                    phone,
                    f"Payment confirmed!\nPlan: {plan}\nThank you, {session.farmer.full_name}!\nReply MENU to return.",
                )
            else:
                svc.mark_failed(session)
                AfricasTalkingClient().send_sms(
                    phone,
                    f"Payment failed: {result_desc}. Please try again. Dial *384# to subscribe.",
                )
    finally:
        db.close()


def _activate_subscription(db, farmer_id: str, plan: str) -> None:
    from app.subscriptions.model import Subscription
    from app.subscriptions.repository import SubscriptionRepository
    import uuid

    repo = SubscriptionRepository(db)
    sub = repo.get_by_farmer_id(uuid.UUID(farmer_id))
    today = datetime.date.today()

    if plan == "Basic":
        end_date = None
    elif plan == "Standard":
        end_date = today + datetime.timedelta(days=30)
    else:  # Premium
        end_date = today + datetime.timedelta(days=30)

    if sub:
        sub.is_active = True
        sub.plan_name = plan
        sub.start_date = today
        sub.end_date = end_date
        repo.update(sub)
        db.commit()
    else:
        sub = Subscription(
            farmer_id=uuid.UUID(farmer_id),
            is_active=True,
            plan_name=plan,
            start_date=today,
            end_date=end_date,
        )
        db.add(sub)
        db.commit()
