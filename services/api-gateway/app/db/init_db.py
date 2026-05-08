from app.db.base import Base
from app.db.session import engine

# Ensure models are imported so they register with SQLAlchemy metadata
from app.db import models  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
