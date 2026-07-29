from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["M-Pesa"])


@router.post("/mpesa/callback")
async def mpesa_callback(request: Request):
    """
    Safaricom Daraja STK Push callback.
    Dispatches subscription activation task.
    """
    body = await request.json()
    stk = body.get("Body", {}).get("stkCallback", {})
    checkout_id = stk.get("CheckoutRequestID", "")
    result_code = stk.get("ResultCode", 1)
    result_desc = stk.get("ResultDesc", "")

    from app.tasks.mpesa_tasks import handle_mpesa_callback
    handle_mpesa_callback.delay(checkout_id, result_code, result_desc)

    return JSONResponse({"ResultCode": 0, "ResultDesc": "Accepted"})
