from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    complaint_type = Column(String(50), nullable=False)
    subject = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    department = Column(String(50), nullable=True)
    priority = Column(String(20), default="Medium")
    status = Column(String(30), default="Pending")
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )


class NetworkMeasurement(Base):
    __tablename__ = "network_measurements"

    id = Column(Integer, primary_key=True, index=True)
    operator = Column(String(50), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    download_mbps = Column(Float)
    upload_mbps = Column(Float)
    rtt_ms = Column(Float)
    network_technology = Column(String(50))
    five_g_frequency_mhz = Column(
    "5g_frequency_mhz",
    Float
)

    five_g_pci = Column(
        "5g_pci",
        Integer
)
    lte_earfcn = Column(Integer)
    cell_event = Column(String(100))