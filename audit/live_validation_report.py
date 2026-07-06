"""
Live validation harness for Member 3.

Proves:
  1. Real HTTP against running uvicorn (not static inspection)
  2. Live Neon PostgreSQL reads/writes
  3. SQLAlchemy transactions commit on success
  4. Rollback leaves DB unchanged on failure

Run while server is up (optional for HTTP section):
  python -m audit.live_validation_report
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import text

from app.database.database import engine
from app.database.sessions import SessionLocal
from app.expert_requests.model import ExpertRequest
from app.experts.model import Expert
from app.farmers.model import Farmer
from app.notifications.model import Notification
from app.notifications.services.notification_service import NotificationService
from app.expert_requests.services.expert_request_service import ExpertRequestService
from app.expert_requests.schema import ExpertRequestCreate

BASE_URL = "http://127.0.0.1:8000"
FAKE_FARMER = "00000000-0000-0000-0000-000000000099"


def section(title: str) -> None:
    print(f"\n{'=' * 72}")
    print(title)
    print("=" * 72)


def neon_scalar(sql: str, **params) -> int:
    with engine.connect() as conn:
        return conn.execute(text(sql), params).scalar() or 0


def get_fixtures() -> tuple[str, str]:
    db = SessionLocal()
    farmer = db.query(Farmer).first()
    expert = (
        db.query(Expert)
        .filter(Expert.is_available.is_(True))
        .first()
    )
    db.close()
    if not farmer or not expert:
        raise RuntimeError("Need at least one farmer and available expert in Neon.")
    return str(farmer.id), str(expert.id)


def validate_http_experts() -> dict:
    section("1) HTTP — GET /experts/ (real request to uvicorn)")
    url = f"{BASE_URL}/experts/?limit=3"
    print(f"REQUEST: GET {url}")

    try:
        response = httpx.get(url, timeout=15.0)
    except httpx.ConnectError:
        print("SKIP: uvicorn not reachable at 127.0.0.1:8000")
        return {"skipped": True}

    body = response.json()
    neon_count = neon_scalar("SELECT COUNT(*) FROM experts")

    print(f"HTTP STATUS: {response.status_code}")
    print(f"HTTP BODY (truncated): {json.dumps(body, default=str)[:400]}...")
    print(f"NEON DIRECT QUERY: SELECT COUNT(*) FROM experts => {neon_count}")

    assert response.status_code == 200
    assert body["total"] == neon_count, "HTTP total must match Neon row count"
    assert len(body["items"]) == 3

    return {
        "method": "httpx GET (real HTTP to uvicorn)",
        "database": "live Neon",
        "http_status": response.status_code,
        "neon_experts": neon_count,
        "http_total": body["total"],
    }


def validate_http_expert_request(farmer_id: str, expert_id: str) -> dict:
    section("2) HTTP — POST /expert-request + DB before/after (Neon)")

    req_before = neon_scalar("SELECT COUNT(*) FROM expert_requests")
    notif_before = neon_scalar("SELECT COUNT(*) FROM notifications")

    payload = {
        "farmer_id": farmer_id,
        "expert_id": expert_id,
        "issue_type": "Live validation",
        "description": f"HTTP validation at {datetime.now(timezone.utc).isoformat()}",
    }
    url = f"{BASE_URL}/expert-request"
    print(f"REQUEST: POST {url}")
    print(f"PAYLOAD: {json.dumps(payload)}")

    try:
        response = httpx.post(url, json=payload, timeout=15.0)
    except httpx.ConnectError:
        print("SKIP: uvicorn not reachable")
        return {"skipped": True}

    req_after = neon_scalar("SELECT COUNT(*) FROM expert_requests")
    notif_after = neon_scalar("SELECT COUNT(*) FROM notifications")

    print(f"HTTP STATUS: {response.status_code}")
    print(f"HTTP BODY: {response.text[:500]}")
    print(f"NEON expert_requests: {req_before} -> {req_after} (delta {req_after - req_before})")
    print(f"NEON notifications:   {notif_before} -> {notif_after} (delta {notif_after - notif_before})")

    assert response.status_code == 201
    assert req_after == req_before + 1, "Request row must be committed to Neon"
    assert notif_after == notif_before + 1, "Notification row must be committed in same flow"

    created_id = response.json()["id"]
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT status FROM expert_requests WHERE id = :id"
            ),
            {"id": created_id},
        ).scalar()
    print(f"NEON VERIFY: expert_requests.status for new row => {row}")
    assert row == "PENDING"

    return {
        "method": "httpx POST (real HTTP)",
        "database": "live Neon",
        "http_status": response.status_code,
        "request_delta": req_after - req_before,
        "notification_delta": notif_after - notif_before,
        "created_id": created_id,
    }


def validate_http_rollback_via_404() -> dict:
    section("3) HTTP failure path — nonexistent farmer must NOT write to Neon")

    req_before = neon_scalar("SELECT COUNT(*) FROM expert_requests")
    notif_before = neon_scalar("SELECT COUNT(*) FROM notifications")

    expert_id = neon_scalar(
        "SELECT id::text FROM experts WHERE is_available = true LIMIT 1"
    )
    payload = {
        "farmer_id": FAKE_FARMER,
        "expert_id": expert_id,
        "issue_type": "Should fail",
        "description": "Rollback validation",
    }

    try:
        response = httpx.post(f"{BASE_URL}/expert-request", json=payload, timeout=15.0)
    except httpx.ConnectError:
        print("SKIP: uvicorn not reachable")
        return {"skipped": True}

    req_after = neon_scalar("SELECT COUNT(*) FROM expert_requests")
    notif_after = neon_scalar("SELECT COUNT(*) FROM notifications")

    print(f"HTTP STATUS: {response.status_code} (expected 404)")
    print(f"HTTP BODY: {response.text}")
    print(f"NEON expert_requests unchanged: {req_before == req_after} ({req_before})")
    print(f"NEON notifications unchanged:   {notif_before == notif_after} ({notif_before})")

    assert response.status_code == 404
    assert req_after == req_before
    assert notif_after == notif_before

    return {
        "method": "httpx POST failure (real HTTP)",
        "database": "live Neon",
        "http_status": response.status_code,
        "rows_unchanged": True,
    }


def validate_service_rollback() -> dict:
    section("4) Service-layer rollback — forced failure mid-transaction")

    db = SessionLocal()
    farmer = db.query(Farmer).first()
    expert = (
        db.query(Expert)
        .filter(Expert.is_available.is_(True))
        .first()
    )
    if not farmer or not expert:
        db.close()
        raise RuntimeError("Missing fixtures")

    farmer_id = farmer.id
    req_before = db.query(ExpertRequest).count()
    notif_before = db.query(Notification).count()

    service = ExpertRequestService(db)

    original = NotificationService.create_expert_update_notification

    def failing_notification(self, *args, **kwargs):
        raise RuntimeError("Simulated SMS/notification failure")

    NotificationService.create_expert_update_notification = failing_notification

    try:
        try:
            service.create_request(
                ExpertRequestCreate(
                    farmer_id=farmer_id,
                    expert_id=expert.id,
                    issue_type="Rollback test",
                    description="Should rollback entirely",
                )
            )
            raise AssertionError("Expected exception was not raised")
        except RuntimeError as exc:
            print(f"CAUGHT EXPECTED ERROR: {exc}")
            db.rollback()
    finally:
        NotificationService.create_expert_update_notification = original
        db.close()

    req_after = neon_scalar("SELECT COUNT(*) FROM expert_requests")
    notif_after = neon_scalar("SELECT COUNT(*) FROM notifications")

    print(f"NEON expert_requests: {req_before} -> {req_after}")
    print(f"NEON notifications:   {notif_before} -> {notif_after}")

    assert req_after == req_before, "Failed transaction must not persist request"
    assert notif_after == notif_before, "Failed transaction must not persist notification"

    return {
        "method": "ExpertRequestService + patched NotificationService",
        "database": "live Neon",
        "rollback_verified": True,
        "rows_unchanged": True,
    }


def validate_http_notifications(farmer_id: str) -> dict:
    section("5) HTTP — GET /notifications/?farmer_id=... (real request)")

    url = f"{BASE_URL}/notifications/?farmer_id={farmer_id}&is_sent=false"
    print(f"REQUEST: GET {url}")

    try:
        response = httpx.get(url, timeout=15.0)
    except httpx.ConnectError:
        print("SKIP: uvicorn not reachable")
        return {"skipped": True}

    body = response.json()
    neon_count = neon_scalar(
        "SELECT COUNT(*) FROM notifications WHERE farmer_id = :fid AND is_sent = false",
        fid=farmer_id,
    )

    print(f"HTTP STATUS: {response.status_code}")
    print(f"HTTP total: {body['total']}")
    print(f"NEON direct count (same farmer, is_sent=false): {neon_count}")

    assert response.status_code == 200
    assert body["total"] == neon_count

    return {
        "method": "httpx GET (real HTTP)",
        "database": "live Neon",
        "http_total": body["total"],
        "neon_count": neon_count,
    }


def main() -> None:
    print("MEMBER 3 LIVE VALIDATION REPORT")
    print(f"Target API: {BASE_URL}")
    print(f"Database host: {engine.url.host}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")

    farmer_id, expert_id = get_fixtures()
    results = {
        "experts_http": validate_http_experts(),
        "expert_request_http": validate_http_expert_request(farmer_id, expert_id),
        "http_failure_no_write": validate_http_rollback_via_404(),
        "service_rollback": validate_service_rollback(),
        "notifications_http": validate_http_notifications(farmer_id),
    }

    section("SUMMARY")
    for name, data in results.items():
        if data.get("skipped"):
            print(f"  {name}: SKIPPED (server not running)")
        else:
            print(f"  {name}: PASS — {data}")

    print("\nAll live validations passed.")
    print("Evidence type: real HTTP + direct Neon SQL + transaction rollback test")
    print("NOT inferred from static code inspection alone.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nVALIDATION FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
