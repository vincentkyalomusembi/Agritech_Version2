"""
M-Pesa Daraja STK Push integration.
Supports sandbox and production environments.
"""
import base64
import datetime

import httpx

from app.core.config import settings

SANDBOX_BASE = "https://sandbox.safaricom.co.ke"
PRODUCTION_BASE = "https://api.safaricom.co.ke"


class MpesaClient:
    def __init__(self):
        self.base_url = SANDBOX_BASE if settings.MPESA_ENV == "sandbox" else PRODUCTION_BASE
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET
        self.shortcode = settings.MPESA_SHORTCODE
        self.passkey = settings.MPESA_PASSKEY
        self.callback_url = settings.MPESA_CALLBACK_URL

    def _get_access_token(self) -> str:
        credentials = base64.b64encode(
            f"{self.consumer_key}:{self.consumer_secret}".encode()
        ).decode()
        response = httpx.get(
            f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": f"Basic {credentials}"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["access_token"]

    def _generate_password(self) -> tuple[str, str]:
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        raw = f"{self.shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(raw.encode()).decode()
        return password, timestamp

    def stk_push(self, phone: str, amount: int, account_ref: str, description: str) -> dict:
        """Initiate an STK push payment request."""
        token = self._get_access_token()
        password, timestamp = self._generate_password()

        normalized = phone.lstrip("+")
        if normalized.startswith("0"):
            normalized = "254" + normalized[1:]

        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": normalized,
            "PartyB": self.shortcode,
            "PhoneNumber": normalized,
            "CallBackURL": self.callback_url,
            "AccountReference": account_ref,
            "TransactionDesc": description,
        }

        response = httpx.post(
            f"{self.base_url}/mpesa/stkpush/v1/processrequest",
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=15,
        )
        response.raise_for_status()
        return response.json()
