from app.database.base import Base
from app.database.database import engine

# Import all models here later
import app.models

def init_db():
    Base.metadata.create_all(bind=engine)