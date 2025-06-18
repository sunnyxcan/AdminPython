# app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime
import os

# Konfigurasi database dari variabel lingkungan
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@host:port/database")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class CustomBase:
    """Base class that provides a dynamically named table name."""
    @declared_attr
    def __tablename__(cls):
        # Default table name, can be overridden in model classes
        return cls.__name__.lower()

    def __init__(self, **kwargs):
        # Override __tablename__ if 'year' is passed to the constructor
        if 'year' in kwargs:
            self.__tablename__ = f"{self.__tablename__}_{kwargs['year']}"
            del kwargs['year'] # Remove 'year' from kwargs to avoid issues
        super().__init__(**kwargs)

    @classmethod
    def set_table_name_for_year(cls, year: int):
        """Set the table name for the current model class based on the year."""
        cls.__tablename__ = f"{cls.__tablename__.split('_')[0]}_{year}"


Base = declarative_base(cls=CustomBase)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()