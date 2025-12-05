"""
Database models for Dubplate Authenticator.

Defines the SQLAlchemy models for storing dubplate authentication data.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class Artist(Base):
    """Model representing an artist who creates dubplates."""
    
    __tablename__ = "artists"
    
    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    dubplates = relationship("Dubplate", back_populates="artist")
    
    def __repr__(self):
        return f"<Artist(id='{self.id}', name='{self.name}')>"


class Dubplate(Base):
    """Model representing a registered dubplate."""
    
    __tablename__ = "dubplates"
    
    id = Column(String(64), primary_key=True)
    artist_id = Column(String(64), ForeignKey("artists.id"), nullable=False)
    title = Column(String(255))
    fingerprint_hash = Column(String(64), nullable=False, index=True)
    watermark_signature = Column(String(64))
    duration = Column(Float)
    sample_rate = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(Text)  # Stored as JSON string
    
    # Relationships
    artist = relationship("Artist", back_populates="dubplates")
    verifications = relationship("Verification", back_populates="dubplate")
    
    def __repr__(self):
        return f"<Dubplate(id='{self.id}', title='{self.title}')>"


class Verification(Base):
    """Model representing a verification attempt."""
    
    __tablename__ = "verifications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dubplate_id = Column(String(64), ForeignKey("dubplates.id"), nullable=True)
    fingerprint_hash = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False)
    confidence = Column(Float)
    ai_probability = Column(Float)
    verified_at = Column(DateTime, default=datetime.utcnow)
    details_json = Column(Text)  # Stored as JSON string
    
    # Relationships
    dubplate = relationship("Dubplate", back_populates="verifications")
    
    def __repr__(self):
        return f"<Verification(id={self.id}, status='{self.status}')>"


class LegacyReference(Base):
    """Model representing a legacy dubplate reference for verification."""
    
    __tablename__ = "legacy_references"
    
    id = Column(String(64), primary_key=True)
    title = Column(String(255))
    artist_name = Column(String(255))
    fingerprint_hash = Column(String(64), nullable=False, index=True)
    spectral_features_json = Column(Text)  # Stored as JSON string
    year = Column(Integer)
    sound_system = Column(String(255))  # Associated sound system
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    
    def __repr__(self):
        return f"<LegacyReference(id='{self.id}', title='{self.title}')>"


def create_database(db_url: str = "sqlite:///dubplate_auth.db") -> tuple:
    """
    Create the database and return engine and session factory.
    
    Args:
        db_url: Database connection URL
        
    Returns:
        Tuple of (engine, Session factory)
    """
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session


def get_session(db_url: str = "sqlite:///dubplate_auth.db"):
    """
    Get a database session.
    
    Args:
        db_url: Database connection URL
        
    Returns:
        Database session
    """
    _, Session = create_database(db_url)
    return Session()
