"""
Production-readiness audit test matrix for experts, requests, and notifications.
Run: python -m audit.test_production_audit
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.database.sessions import SessionLocal
from app.expert_requests.model import RequestStatus
from app.experts.model import Expert
from app.main import app
from app.subscriptions.services.subscription_service import SubscriptionService

client = TestClient(app)
FAKE_UUID = "00000000-0000-0000-0000-000000000099"
results: list[tuple[str, bool, str]] = []


def record(name: str, passed: bool, detail: str = "") -> None:
    results.append((name, passed, detail))
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))


def get_test_context():
    db = SessionLocal()
    from app.farmers.model import Farmer
    from sqlalchemy import text

    farmer = db.query(Farmer).first()
    expert = (
        db.query(Expert)
        .filter(Expert.is_available.is_(True))
        .first()
    )
    unavailable = (
        db.query(Expert)
        .filter(Expert.is_available.is_(False))
        .first()
    )
    if unavailable is None and expert is not None:
        unavailable = expert
        unavailable.is_available = False
        db.commit()
        db.refresh(unavailable)
        expert = (
            db.query(Expert)
            .filter(Expert.is_available.is_(True))
            .first()
        )
    county_id = None
    if expert:
        county_id = str(expert.county_id)
    farmer_id = str(farmer.id) if farmer else None
    expert_id = str(expert.id) if expert else None
    unavailable_id = str(unavailable.id) if unavailable else None
    db.close()
    return farmer_id, expert_id, unavailable_id, county_id


def run_tests() -> None:
    farmer_id, expert_id, unavailable_id, county_id = get_test_context()

    # --- Experts ---
    r = client.get("/experts/", params={"limit": 5})
    record("valid GET /experts", r.status_code == 200 and r.json()["total"] > 0)

    r = client.get("/experts/")
    data = r.json()
    record(
        "default experts pagination cap",
        r.status_code == 200 and len(data["items"]) <= 100 and data["limit"] == 100,
    )

    r = client.get("/experts/", params={"county_id": county_id, "expert_type": "Agriculture", "limit": 3})
    record("experts filtered by county + type", r.status_code == 200)

    r = client.get("/experts/", params={"county_id": "not-a-uuid"})
    record("invalid UUID query param", r.status_code == 422)

    r = client.get("/experts/", params={"expert_type": "InvalidType"})
    record("invalid enum expert_type", r.status_code == 422)

    r = client.get("/experts/", params={"limit": 2, "offset": 1})
    data = r.json()
    record(
        "pagination limit/offset",
        r.status_code == 200 and len(data["items"]) <= 2 and data["offset"] == 1,
    )

    # --- Expert requests ---
    r = client.post("/expert-request", json={})
    record("malformed expert-request payload", r.status_code == 422)

    r = client.post(
        "/expert-request",
        json={
            "farmer_id": FAKE_UUID,
            "expert_id": expert_id or FAKE_UUID,
            "issue_type": "x",
            "description": "y",
        },
    )
    record("nonexistent farmer", r.status_code == 404, r.text[:120])

    r = client.post(
        "/expert-request",
        json={
            "farmer_id": farmer_id,
            "expert_id": FAKE_UUID,
            "issue_type": "x",
            "description": "y",
        },
    )
    record("nonexistent expert", r.status_code == 404, r.text[:120])

    if farmer_id and unavailable_id:
        r = client.post(
            "/expert-request",
            json={
                "farmer_id": farmer_id,
                "expert_id": unavailable_id,
                "issue_type": "x",
                "description": "unavailable expert test",
            },
        )
        record("unavailable expert", r.status_code == 400, r.text[:120])

    created_id = None
    if farmer_id and expert_id:
        r = client.post(
            "/expert-request",
            json={
                "farmer_id": farmer_id,
                "expert_id": expert_id,
                "issue_type": "Pest",
                "description": "Audit valid request",
            },
        )
        record("valid expert-request create", r.status_code == 201, r.text[:120])
        if r.status_code == 201:
            created_id = r.json()["id"]

        r = client.post(
            "/expert-request",
            json={
                "farmer_id": farmer_id,
                "expert_id": expert_id,
                "issue_type": "Pest",
                "description": "Duplicate request allowed",
            },
        )
        record("duplicate expert-request (allowed)", r.status_code == 201)

    if created_id:
        r = client.patch(
            "/expert-request/status",
            json={"request_id": created_id, "status": "Accepted"},
        )
        record("valid status transition Pending->Accepted", r.status_code == 200)

        r = client.patch(
            "/expert-request/status",
            json={"request_id": created_id, "status": "Pending"},
        )
        record("invalid status transition Accepted->Pending", r.status_code == 400)

        r = client.patch(
            "/expert-request/status",
            json={"request_id": created_id, "status": "Accepted"},
        )
        record("idempotent duplicate status update", r.status_code == 200)

    r = client.patch(
        "/expert-request/status",
        json={"request_id": FAKE_UUID, "status": "Accepted"},
    )
    record("missing expert request", r.status_code == 404)

    r = client.patch("/expert-request/status", json={"request_id": "bad", "status": "Accepted"})
    record("invalid UUID in status update", r.status_code == 422)

    # --- Notifications ---
    r = client.get("/notifications/")
    record("notifications without farmer_id rejected", r.status_code == 400, r.text[:120])

    if farmer_id:
        r = client.get("/notifications/", params={"farmer_id": farmer_id})
        record("valid notifications list", r.status_code == 200 and r.json()["total"] >= 1)

        r = client.get(
            "/notifications/",
            params={
                "farmer_id": farmer_id,
                "notification_type": "Expert Update",
                "is_sent": False,
            },
        )
        record("notification filtering", r.status_code == 200)

    r = client.get("/notifications/", params={"farmer_id": FAKE_UUID})
    record("notifications for nonexistent farmer (empty)", r.status_code == 200 and r.json()["total"] == 0)

    # --- Subscriptions (service layer) ---
    if farmer_id:
        db = SessionLocal()
        svc = SubscriptionService(db)
        from uuid import UUID

        fid = UUID(farmer_id)
        sub = svc.activate_subscription(fid)
        record("subscription activate", sub.is_active is True)
        record("premium active", svc.is_premium_active(fid) is True)

        sub = svc.deactivate_subscription(fid)
        record("inactive subscription", sub.is_active is False and svc.is_premium_active(fid) is False)

        expired_end = date.today() - timedelta(days=1)
        expired_start = expired_end - timedelta(days=30)
        svc.activate_subscription(
            fid,
            start_date=expired_start,
            end_date=expired_end,
        )
        record("expired subscription auto-deactivate", svc.is_premium_active(fid) is False)
        db.close()

    failed = [name for name, passed, _ in results if not passed]
    print("\n=== SUMMARY ===")
    print(f"Total: {len(results)} | Passed: {len(results) - len(failed)} | Failed: {len(failed)}")
    if failed:
        print("Failures:", ", ".join(failed))
        raise SystemExit(1)


if __name__ == "__main__":
    run_tests()
