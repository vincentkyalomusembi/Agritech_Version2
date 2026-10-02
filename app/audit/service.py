from uuid import UUID

from sqlalchemy.orm import Session

from app.audit.model import AuditLog


def write_audit(
    db: Session,
    *,
    action: str,
    entity: str,
    entity_id: str | UUID | None = None,
    actor_id: UUID | None = None,
    actor_kind: str = "staff",
    metadata: dict | None = None,
    commit: bool = False,
) -> AuditLog:
    row = AuditLog(
        actor_id=actor_id,
        actor_kind=actor_kind,
        action=action,
        entity=entity,
        entity_id=str(entity_id) if entity_id is not None else None,
        metadata_json=metadata or {},
    )
    db.add(row)
    if commit:
        db.commit()
        db.refresh(row)
    return row
