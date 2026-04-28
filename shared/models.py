"""
Database models for ElevatorAI ADK
"""
from sqlalchemy import create_engine, Column, String, Float, Integer, JSON, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(50), primary_key=True)
    phone = Column(String(20), unique=True, index=True)
    name = Column(String(200))
    email = Column(String(200))
    location = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_interaction = Column(DateTime, default=datetime.utcnow)

class CabinDesign(Base):
    __tablename__ = "cabin_designs"

    id = Column(String(50), primary_key=True)
    name = Column(String(200), nullable=False)
    style_tags = Column(JSON)
    materials = Column(JSON)
    color_palette = Column(JSON)
    price_usd = Column(Float)
    dimensions = Column(JSON)
    capacity = Column(Integer)
    features = Column(JSON)
    thumbnail_url = Column(String(500))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class DesignSession(Base):
    __tablename__ = "design_sessions"

    id = Column(String(50), primary_key=True)
    customer_id = Column(String(50))
    vision_analysis = Column(JSON)
    matched_cabins = Column(JSON)
    selected_cabin_id = Column(String(50))
    generated_model_url = Column(String(500))
    quote_id = Column(String(50))
    status = Column(String(50), default="started")
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

class Quote(Base):
    __tablename__ = "quotes"

    id = Column(String(50), primary_key=True)
    session_id = Column(String(50))
    customer_id = Column(String(50))
    cabin_id = Column(String(50))
    breakdown = Column(JSON)
    total = Column(Float)
    currency = Column(String(3), default="USD")
    status = Column(String(50), default="sent")
    valid_until = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"

    id = Column(String(50), primary_key=True)
    customer_phone = Column(String(20))
    direction = Column(String(10))  # inbound, outbound
    message_type = Column(String(20))
    content = Column(Text)
    template_name = Column(String(100))
    status = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)

# Database setup
def init_database(database_url: str = None):
    """Initialize database tables"""
    if not database_url:
        database_url = "postgresql://user:pass@localhost:5432/elevatorai_adk"

    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)
