"""Shared SQLAlchemy engine. Override with DATABASE_URL env var if needed."""
import os
from sqlalchemy import create_engine

DB_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/olist_dwh")
engine = create_engine(DB_URL, future=True)
