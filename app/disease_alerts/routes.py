from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.audit.service import write_audit
from app.auth.dependencies import get_current_farmer
from app.database.sessions import SessionLocal, get_db
from app.disease_alerts.model import OutbreakAlert
from app.disease_alerts.schema import AlertDraft, AlertResponse, RecipientPreview, SignalCell, Thresholds
from app.disease_alerts.service import OutbreakService
from app.farmers.location import farmer_coordinates
from app.farmers.model import Farmer
from app.staff.dependencies import get_current_staff, require_roles
from app.staff.model import StaffRole, StaffUser

router = APIRouter(tags=["Outbreaks"])
admin_only = require_roles(StaffRole.PLATFORM_ADMIN)


def _deliver(messages: list[tuple[str, str]]) -> None:
    db = SessionLocal()
    try:
        OutbreakService(db).deliver(messages)
    finally:
        db.close()


@router.get("/admin/outbreak-signals", response_model=list[SignalCell])
def outbreak_signals(
    symptom_code: str | None = Query(default=None, max_length=60),
    issue_type: str | None = Query(default=None, pattern=r"^(crop|livestock)$"),
    from_week: date | None = None,
    through_week: date | None = None,
    _: StaffUser = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """Expert-request reports grouped into grid cells per week; single-report cells are withheld."""
    return OutbreakService(db).signals(symptom_code, issue_type, from_week, through_week)


@router.get("/admin/outbreak-thresholds", response_model=Thresholds)
def get_thresholds(_: StaffUser = Depends(get_current_staff), db: Session = Depends(get_db)):
    row = OutbreakService(db).thresholds()
    return Thresholds(minimum_count=row.minimum_count, cell_size_deg=row.cell_size_deg)


@router.patch("/admin/outbreak-thresholds", response_model=Thresholds)
def update_thresholds(payload: Thresholds, staff: StaffUser = Depends(admin_only), db: Session = Depends(get_db)):
    row = OutbreakService(db).update_thresholds(payload.minimum_count, payload.cell_size_deg, staff.id)
    write_audit(db, action="outbreak.thresholds", entity="outbreak_settings", entity_id="1", actor_id=staff.id,
                metadata=payload.model_dump(), commit=True)
    return Thresholds(minimum_count=row.minimum_count, cell_size_deg=row.cell_size_deg)


@router.get("/admin/outbreak-alerts", response_model=list[AlertResponse])
def list_alerts(_: StaffUser = Depends(get_current_staff), db: Session = Depends(get_db)):
    rows = db.query(OutbreakAlert).order_by(OutbreakAlert.created_at.desc()).limit(200).all()
    return [OutbreakService.to_response(row) for row in rows]


@router.post("/admin/outbreak-alerts/preview", response_model=RecipientPreview)
def preview_alert(draft: AlertDraft, _: StaffUser = Depends(admin_only), db: Session = Depends(get_db)):
    """How many active farmers fall inside the alert radius."""
    return RecipientPreview(recipient_count=len(OutbreakService(db).recipients(draft.center_lat, draft.center_lng, draft.radius_km)))


@router.post("/admin/outbreak-alerts", response_model=AlertResponse, status_code=201)
def send_alert(draft: AlertDraft, background_tasks: BackgroundTasks, staff: StaffUser = Depends(admin_only), db: Session = Depends(get_db)):
    """Send to every farmer in the radius: inbox notification now, SMS after the response."""
    alert, messages = OutbreakService(db).send_alert(draft, staff.id)
    write_audit(db, action="outbreak.alert.send", entity="outbreak_alert", entity_id=alert.id, actor_id=staff.id,
                metadata={"recipients": alert.recipient_count, "radius_km": alert.radius_km}, commit=True)
    background_tasks.add_task(_deliver, messages)
    return OutbreakService.to_response(alert)


@router.get("/outbreak-alerts/nearby", response_model=list[AlertResponse])
def nearby_alerts(
    latitude: float | None = Query(default=None, ge=-4.7, le=5.1),
    longitude: float | None = Query(default=None, ge=33.9, le=41.9),
    current_farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    """Active alerts covering a point, defaulting to the signed-in farmer's farm."""
    if latitude is None or longitude is None:
        latitude, longitude, _ = farmer_coordinates(current_farmer)
    if latitude is None or longitude is None:
        raise HTTPException(status_code=422, detail="Add your farm location to see nearby alerts.")
    return [OutbreakService.to_response(alert) for alert in OutbreakService(db).active_alerts_near(latitude, longitude)]
