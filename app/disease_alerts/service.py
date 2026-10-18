import math
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session, joinedload

from app.core.africas_talking import AfricasTalkingClient
from app.disease_alerts.model import OutbreakAlert, OutbreakSettings
from app.expert_requests.model import ExpertRequest
from app.farmers.location import farmer_coordinates
from app.farmers.model import Farmer
from app.notifications.model import Notification, NotificationType
from app.recommendations.vendor_matching import distance_km

DEFAULT_MINIMUM_COUNT = 3
DEFAULT_CELL_SIZE_DEG = 0.1
# Never expose a cell built from a single report: it would point at one farm.
PRIVACY_MINIMUM = 2
ALERT_LIFETIME = timedelta(days=30)


def week_start(moment: datetime) -> str:
    day = moment.date() if isinstance(moment, datetime) else moment
    return (day - timedelta(days=day.weekday())).isoformat()


def issue_type_of(request: ExpertRequest) -> str:
    return "livestock" if request.issue_type.lower().startswith(("livestock", "veterinary", "animal")) else "crop"


class OutbreakService:
    def __init__(self, db: Session, sms: AfricasTalkingClient | None = None):
        self.db = db
        self.sms = sms or AfricasTalkingClient()

    # ── Thresholds ───────────────────────────────────────────────────

    def thresholds(self) -> OutbreakSettings:
        row = self.db.get(OutbreakSettings, 1)
        if row is None:
            row = OutbreakSettings(id=1, minimum_count=DEFAULT_MINIMUM_COUNT, cell_size_deg=DEFAULT_CELL_SIZE_DEG)
            self.db.add(row)
            self.db.commit()
        return row

    def update_thresholds(self, minimum_count: int, cell_size_deg: float, staff_id) -> OutbreakSettings:
        row = self.thresholds()
        row.minimum_count, row.cell_size_deg, row.updated_by = minimum_count, cell_size_deg, staff_id
        self.db.commit()
        return row

    # ── Signals ──────────────────────────────────────────────────────

    def signals(self, symptom_code: str | None = None, issue_type: str | None = None,
                from_week: date | None = None, through_week: date | None = None) -> list[dict]:
        settings = self.thresholds()
        size = settings.cell_size_deg
        through = (through_week or date.today()) + timedelta(days=7)
        start = from_week or (date.today() - timedelta(weeks=8))
        requests = (
            self.db.query(ExpertRequest)
            .options(joinedload(ExpertRequest.farmer).joinedload(Farmer.county))
            .filter(ExpertRequest.created_at >= start, ExpertRequest.created_at < through)
            .all()
        )
        cells: dict[tuple, dict] = {}
        for request in requests:
            kind = issue_type_of(request)
            if issue_type and kind != issue_type:
                continue
            codes = request.symptom_codes or ["unspecified"]
            if symptom_code and symptom_code not in codes:
                continue
            latitude, longitude, _ = farmer_coordinates(request.farmer)
            if latitude is None or longitude is None:
                continue
            row, col = math.floor(latitude / size), math.floor(longitude / size)
            week = week_start(request.created_at)
            cell = cells.setdefault((kind, week, row, col), {
                "cell_id": f"{kind}:{week}:{row}:{col}",
                "center_lat": round((row + 0.5) * size, 5), "center_lng": round((col + 0.5) * size, 5),
                "count": 0, "by_symptom": defaultdict(int), "issue_type": kind, "week_start": week,
            })
            cell["count"] += 1
            for code in codes:
                cell["by_symptom"][code] += 1
        visible = [cell for cell in cells.values() if cell["count"] >= PRIVACY_MINIMUM]
        for cell in visible:
            cell["by_symptom"] = dict(cell["by_symptom"])
            cell["flagged"] = cell["count"] >= settings.minimum_count
        return sorted(visible, key=lambda cell: (cell["week_start"], -cell["count"]), reverse=True)

    # ── Alerts ───────────────────────────────────────────────────────

    def recipients(self, latitude: float, longitude: float, radius_km: float) -> list[Farmer]:
        farmers = (
            self.db.query(Farmer)
            .options(joinedload(Farmer.county), joinedload(Farmer.constituency))
            .filter(Farmer.is_active.is_(True))
            .all()
        )
        inside = []
        for farmer in farmers:
            lat, lng, _ = farmer_coordinates(farmer)
            if lat is not None and lng is not None and distance_km(latitude, longitude, lat, lng) <= radius_km:
                inside.append(farmer)
        return inside

    def send_alert(self, draft, staff_id) -> tuple[OutbreakAlert, list[tuple[str, str]]]:
        """Record the alert and inbox notifications; returns SMS (phone, text) to send afterwards."""
        farmers = self.recipients(draft.center_lat, draft.center_lng, draft.radius_km)
        now = datetime.now(timezone.utc)
        alert = OutbreakAlert(
            symptom_code=draft.symptom_code, issue_type=draft.issue_type, subject_key=draft.subject_key,
            center_lat=draft.center_lat, center_lng=draft.center_lng, radius_km=draft.radius_km,
            message_en=draft.message.en, message_sw=draft.message.sw, status="sent",
            recipient_count=len(farmers), created_by=staff_id, expires_at=now + ALERT_LIFETIME,
        )
        self.db.add(alert)
        text = f"AgriTech alert: {draft.message.en}\n{draft.message.sw}"
        for farmer in farmers:
            self.db.add(Notification(
                farmer_id=farmer.id, notification_type=NotificationType.DISEASE_ALERT,
                title="Disease / pest alert near your farm"[:150], message=f"{draft.message.en}\n\n{draft.message.sw}",
                is_sent=True, sent_at=now, delivery_status="Submitted",
            ))
        self.db.commit()
        self.db.refresh(alert)
        return alert, [(farmer.phone_number, text) for farmer in farmers]

    def deliver(self, messages: list[tuple[str, str]]) -> None:
        for phone, text in messages:
            self.sms.send_sms(phone, text)

    def active_alerts_near(self, latitude: float, longitude: float) -> list[OutbreakAlert]:
        now = datetime.now(timezone.utc)
        alerts = self.db.query(OutbreakAlert).filter(OutbreakAlert.status == "sent", OutbreakAlert.expires_at > now) \
            .order_by(OutbreakAlert.created_at.desc()).all()
        return [alert for alert in alerts if distance_km(latitude, longitude, alert.center_lat, alert.center_lng) <= alert.radius_km]

    @staticmethod
    def to_response(alert: OutbreakAlert) -> dict:
        return {
            "id": alert.id, "symptom_code": alert.symptom_code, "issue_type": alert.issue_type,
            "subject_key": alert.subject_key, "center_lat": alert.center_lat, "center_lng": alert.center_lng,
            "radius_km": alert.radius_km, "message": {"en": alert.message_en, "sw": alert.message_sw},
            "status": alert.status, "recipient_count": alert.recipient_count, "created_by": alert.created_by,
            "created_at": alert.created_at, "expires_at": alert.expires_at,
        }
