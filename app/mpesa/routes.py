from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from app.core.webhooks import verify_webhook_secret

router = APIRouter(tags=["M-Pesa"])


@router.post("/mpesa/callback")
async def mpesa_callback(
    request: Request,
    webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
):
    """
    Safaricom Daraja STK Push callback.
    Dispatches subscription activation task.
    """
    verify_webhook_secret(webhook_secret)
    body = await request.json()
    stk = body.get("Body", {}).get("stkCallback", {})
    checkout_id = stk.get("CheckoutRequestID", "")
    result_code = stk.get("ResultCode", 1)
    result_desc = stk.get("ResultDesc", "")

    from app.tasks.mpesa_tasks import handle_mpesa_callback
    handle_mpesa_callback.delay(checkout_id, result_code, result_desc)

    return JSONResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
