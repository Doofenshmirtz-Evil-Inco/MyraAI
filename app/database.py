import io
import os
from datetime import datetime

import pandas as pd
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'voicelog.db')}")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class MovieLog(Base):
    __tablename__ = "movie_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    year = Column(String)
    tmdb_id = Column(Integer)
    rating = Column(Float)
    watched_date = Column(String)
    rewatch = Column(Boolean, default=False)
    review = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


Base.metadata.create_all(bind=engine)


def migrate_legacy_csv():
    legacy_path = os.path.join(BASE_DIR, "letterboxd_import.csv")
    if not os.path.exists(legacy_path):
        return

    legacy_rows = pd.read_csv(legacy_path).fillna("").to_dict("records")
    db = SessionLocal()
    try:
        existing = {(log.title, str(log.year), log.tmdb_id) for log in db.query(MovieLog).all()}
        for row in legacy_rows:
            key = (row.get("Title"), str(row.get("Year", "")), row.get("tmdbID"))
            if key in existing:
                continue
            db.add(MovieLog(
                session_id="legacy-csv",
                title=row.get("Title"),
                year=str(row.get("Year", "")),
                tmdb_id=int(row["tmdbID"]) if row.get("tmdbID") != "" else None,
                rating=float(row["Rating"]) if row.get("Rating") != "" else None,
                watched_date=row.get("WatchedDate", ""),
                rewatch=str(row.get("Rewatch", "")).casefold() == "true",
                review=row.get("Review", ""),
            ))
        db.commit()
    finally:
        db.close()


migrate_legacy_csv()


def save_log_to_db(entry: dict, session_id: str = "default"):
    db = SessionLocal()
    try:
        db.add(MovieLog(
            session_id=session_id,
            title=entry.get("Title"),
            year=entry.get("Year"),
            tmdb_id=entry.get("tmdbID"),
            rating=entry.get("Rating"),
            watched_date=entry.get("WatchedDate"),
            rewatch=entry.get("Rewatch", False),
            review=entry.get("Review", ""),
        ))
        db.commit()
    finally:
        db.close()


def export_to_csv_bytes() -> bytes:
    db = SessionLocal()
    try:
        logs = db.query(MovieLog).order_by(MovieLog.created_at, MovieLog.id).all()
        rows = [{
            "Title": log.title,
            "Year": log.year,
            "tmdbID": log.tmdb_id,
            "Rating": log.rating,
            "WatchedDate": log.watched_date,
            "Rewatch": log.rewatch,
            "Review": log.review,
        } for log in logs]
    finally:
        db.close()

    frame = pd.DataFrame(rows, columns=["Title", "Year", "tmdbID", "Rating", "WatchedDate", "Rewatch", "Review"])
    output = io.StringIO()
    frame.to_csv(output, index=False)
    return output.getvalue().encode("utf-8")
