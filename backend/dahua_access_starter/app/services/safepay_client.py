from __future__ import annotations

import threading
import time
from typing import Any

import requests

from app.core.config import (
    SAFEPAY_HOST,
    SAFEPAY_MERCHANT_API_KEY,
    SAFEPAY_SECRET_KEY,
    SAFEPAY_TIMEOUT_SECONDS,
)


class SafepayAPIError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, response: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class SafepayClient:
    """Small server-side client for Safepay Raast Dynamic QR APIs."""

    def __init__(self) -> None:
        self.host = SAFEPAY_HOST.rstrip("/")
        self.secret_key = SAFEPAY_SECRET_KEY
        self.merchant_api_key = SAFEPAY_MERCHANT_API_KEY
        self.timeout = SAFEPAY_TIMEOUT_SECONDS
        self._checkout_token: str | None = None
        self._checkout_token_expires_at = 0.0
        self._token_lock = threading.Lock()

    def _require_credentials(self) -> None:
        if not self.secret_key or not self.merchant_api_key:
            raise SafepayAPIError(
                "Safepay is not configured. Set SAFEPAY_SECRET_KEY and SAFEPAY_MERCHANT_API_KEY in .env."
            )

    def _request(self, method: str, path: str, *, token: str | None = None, json_body: dict | None = None) -> dict:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        else:
            headers["X-SFPY-MERCHANT-SECRET"] = self.secret_key
        url = f"{self.host}{path}"
        try:
            response = requests.request(
                method, url, headers=headers, json=json_body, timeout=self.timeout
            )
        except requests.RequestException as exc:
            raise SafepayAPIError(f"Could not connect to Safepay: {exc}") from exc
        try:
            payload = response.json()
        except ValueError:
            payload = {"raw_response": response.text[:1000]}
        if not response.ok:
            detail = payload.get("detail") or payload.get("message") or payload.get("status") or payload
            raise SafepayAPIError(
                f"Safepay returned HTTP {response.status_code}: {str(detail)[:700]}",
                status_code=response.status_code,
                response=payload,
            )
        if not isinstance(payload, dict):
            raise SafepayAPIError("Safepay returned an unexpected response format.", response=payload)
        return payload

    def _get_checkout_token(self) -> str:
        self._require_credentials()
        now = time.monotonic()
        if self._checkout_token and now < self._checkout_token_expires_at:
            return self._checkout_token
        with self._token_lock:
            now = time.monotonic()
            if self._checkout_token and now < self._checkout_token_expires_at:
                return self._checkout_token
            response = self._request("POST", "/client/passport/v1/token", json_body={})
            token = response.get("data")
            if not isinstance(token, str) or not token:
                raise SafepayAPIError("Safepay did not return a checkout authentication token.", response=response)
            # Safepay documents a one-hour token. Refresh five minutes early.
            self._checkout_token = token
            self._checkout_token_expires_at = time.monotonic() + (55 * 60)
            return token

    def create_raast_dynamic_qr(self, *, amount_minor: int, expiry_minutes: int) -> dict:
        self._require_credentials()
        tracker_response = self._request(
            "POST",
            "/order/payments/v3/",
            json_body={
                "merchant_api_key": self.merchant_api_key,
                "intent": "RAAST",
                "mode": "payment",
                "entry_mode": "raw",
                "currency": "PKR",
                "amount": amount_minor,
            },
        )
        tracker = (tracker_response.get("data") or {}).get("tracker") or {}
        tracker_token = tracker.get("token")
        if not tracker_token:
            raise SafepayAPIError("Safepay did not return a payment tracker.", response=tracker_response)
        capabilities = (tracker_response.get("data") or {}).get("capabilities") or {}
        if capabilities.get("RAAST") is not True:
            raise SafepayAPIError(
                "Raast is not enabled for this Safepay sandbox merchant. Ask Safepay to enable Raast for your account.",
                response=tracker_response,
            )

        checkout_token = self._get_checkout_token()
        qr_response = self._request(
            "POST",
            f"/order/payments/v3/{tracker_token}",
            token=checkout_token,
            json_body={"payload": {"raast": {"kind": "DYNAMIC_QR", "expiry_in_minutes": expiry_minutes}}},
        )
        qr_tracker = (qr_response.get("data") or {}).get("tracker") or {}
        raast_payment = qr_tracker.get("raast_payment") or {}
        qr_code = raast_payment.get("qr_code") or {}
        code = qr_code.get("code")
        if not isinstance(code, str) or not code:
            raise SafepayAPIError("Safepay did not return the Dynamic QR payload.", response=qr_response)
        return {
            "tracker_token": tracker_token,
            "qr_payload": code,
            "tracker_response": tracker_response,
            "qr_response": qr_response,
            "raast_payment": raast_payment,
            "tracker": qr_tracker,
        }

    def get_tracker_status(self, tracker_token: str) -> dict:
        checkout_token = self._get_checkout_token()
        return self._request(
            "GET",
            f"/order/payments/v3/{tracker_token}/status",
            token=checkout_token,
        )


safepay_client = SafepayClient()
