from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
from app.config import settings

if settings.use_sqlite:
    engine = create_engine(
        settings.database_url,
        echo=False,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(
        settings.database_url,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from app.models import user, knowledge, course, quiz, face, schedule  # noqa
    Base.metadata.create_all(bind=engine)
    # Migrate existing tables for new columns
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE exam_results ADD COLUMN time_limit INTEGER DEFAULT 1800"))
            conn.commit()
    except Exception:
        pass  # Column already exists
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE quiz_questions ADD COLUMN exam_id INTEGER DEFAULT NULL"))
            conn.commit()
    except Exception:
        pass  # Column already exists
