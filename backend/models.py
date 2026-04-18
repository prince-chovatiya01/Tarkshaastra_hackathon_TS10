# ORM models for Ghost Water Detector — all tables from Sections 3 and 4
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Index, func
from geoalchemy2 import Geometry
from backend.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(String(30), nullable=False)
    assigned_zone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class CrewMember(Base):
    __tablename__ = "crew_members"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    zone = Column(String(50), nullable=False)
    is_available = Column(Boolean, default=True)
    current_dispatch_id = Column(Integer, nullable=True)
    telegram_chat_id = Column(String(50), nullable=True)


class Zone(Base):
    __tablename__ = "zones"
    id = Column(Integer, primary_key=True, index=True)
    zone_name = Column(String(50), unique=True, nullable=False)
    geom = Column(Geometry("POLYGON", srid=4326))


class PipeSegment(Base):
    __tablename__ = "pipe_segments"
    id = Column(Integer, primary_key=True, index=True)
    segment_id = Column(String(20), unique=True, nullable=False)
    zone = Column(String(50), nullable=False)
    ward_name = Column(String(100))
    geom = Column(Geometry("GEOMETRY", srid=4326))
    length_m = Column(Float, default=50.0)
    __table_args__ = (Index("idx_pipe_geom", geom, postgresql_using="gist"),)


class SensorReading(Base):
    __tablename__ = "sensor_readings"
    id = Column(Integer, primary_key=True, index=True)
    segment_id = Column(String(20), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    pressure_value = Column(Float, nullable=False)
    flow_rate = Column(Float)
    is_peak_hour = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (Index("idx_sensor_time", "segment_id", "timestamp"),)


class Anomaly(Base):
    __tablename__ = "anomalies"
    id = Column(Integer, primary_key=True, index=True)
    segment_id = Column(String(20), ForeignKey("pipe_segments.segment_id"))
    detected_at = Column(DateTime, server_default=func.now())
    anomaly_type = Column(String(30), nullable=False)
    urgency = Column(String(10), nullable=False)
    confidence = Column(Float)
    est_loss_litres = Column(Float, nullable=False)
    is_false_positive = Column(Boolean, default=False)
    zone = Column(String(50), nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    status = Column(String(20), default="ACTIVE")


class DispatchLog(Base):
    __tablename__ = "dispatch_logs"
    id = Column(Integer, primary_key=True, index=True)
    anomaly_id = Column(Integer, ForeignKey("anomalies.id"))
    segment_id = Column(String(20))
    dispatched_at = Column(DateTime, server_default=func.now())
    dispatched_by = Column(Integer, ForeignKey("users.id"))
    crew_member_id = Column(Integer, ForeignKey("crew_members.id"))
    message_sid = Column(String(50))
    zone = Column(String(50))
    anomaly_type = Column(String(30))
    urgency = Column(String(10))
    status = Column(String(20), default="SENT")
    crew_response = Column(String(30))
    resolved_at = Column(DateTime)
    timeout_at = Column(DateTime)
