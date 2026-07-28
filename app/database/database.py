from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    # ---- Copilot Improvement ----
    # Disable SQL echoing in normal operation to avoid leaking query values and
    # reduce log volume; pool settings reuse healthy production connections.
    # ---- End Improvement ----
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
