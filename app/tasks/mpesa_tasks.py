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
        from app.sms_sessions.model import SMSSession
        session = db.query(SMSSession).filter_by(id=session_id).first()
        _activate_subscription(db, farmer_id, plan, session=session)
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
                _activate_subscription(db, str(session.farmer_id), plan, session=session)
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


def _activate_subscription(db, farmer_id: str, plan: str, session=None) -> None:
    from uuid import UUID

    from app.pricing.engine import normalize_plan_name
    from app.pricing.service import QuoteService
    from app.subscriptions.services.subscription_service import SubscriptionService
    import json

    today = datetime.date.today()
    quote_id = None
    amount_kes = None
    size_class = normalize_plan_name(plan)
    rule_version = None

    if session and session.session_data:
        data = json.loads(session.session_data)
        raw_quote_id = data.get("quote_id")
        if raw_quote_id:
            quote = QuoteService(db).get_by_id(UUID(raw_quote_id))
            if quote:
                quote_id = quote.id
                amount_kes = quote.amount_kes
                size_class = quote.size_class
                rule_version = quote.rule_version
                QuoteService(db).mark_paid(quote, commit=False)

    if size_class == "Micro" or (amount_kes == 0):
        end_date = None
    else:
        end_date = today + datetime.timedelta(days=30)

    SubscriptionService(db).activate_subscription(
        farmer_id=UUID(farmer_id),
        plan_name=size_class,
        start_date=today,
        end_date=end_date,
        size_class=size_class,
        amount_kes=amount_kes if amount_kes is not None else (0 if size_class == "Micro" else None),
        quote_id=quote_id,
        rule_version=rule_version,
        commit=True,
    )
