# Pydantic request/response schemas
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    token: str
    role: str
    full_name: str
    assigned_zone: Optional[str] = None


class UserOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    role: str
    assigned_zone: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class AnomalyCreate(BaseModel):
    segment_id: str
    anomaly_type: str
    urgency: str
    confidence: float
    est_loss_litres: float
    zone: str
    lat: float
    lng: float


class AnomalyOut(BaseModel):
    id: int
    segment_id: str
    detected_at: Optional[datetime] = None
    anomaly_type: str
    urgency: str
    confidence: Optional[float] = None
    est_loss_litres: float
    is_false_positive: bool
    zone: str
    lat: float
    lng: float
    status: str

    class Config:
        from_attributes = True


class AnomalyFilter(BaseModel):
    zone: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    anomaly_type: Optional[str] = None


class DispatchRequest(BaseModel):
    anomaly_id: int
    crew_member_id: int


class DispatchOut(BaseModel):
    id: int
    anomaly_id: int
    segment_id: Optional[str] = None
    dispatched_at: Optional[datetime] = None
    crew_member_id: int
    zone: Optional[str] = None
    anomaly_type: Optional[str] = None
    urgency: Optional[str] = None
    status: str
    crew_response: Optional[str] = None
    resolved_at: Optional[datetime] = None
    timeout_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CrewMemberOut(BaseModel):
    id: int
    name: str
    phone: str
    zone: str
    is_available: bool

    class Config:
        from_attributes = True


class KPIResponse(BaseModel):
    total_active_anomalies: int
    total_daily_loss_litres: float
    zone_nrw: dict
