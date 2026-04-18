# Dashboard router — KPI and anomaly list endpoints, role-gated to all 3 roles
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List
from backend.database import get_db
from backend.models import Anomaly, User
from backend.schemas import KPIResponse, AnomalyOut
from backend.auth import require_role

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

all_roles = require_role("utility_manager", "zone_engineer", "data_analyst")


@router.get("/kpis", response_model=KPIResponse)
def get_kpis(db: Session = Depends(get_db), user: User = Depends(all_roles)):
    active = db.query(Anomaly).filter(Anomaly.status == "ACTIVE").all()

    zone_filter = None
    if user.role == "zone_engineer" and user.assigned_zone:
        zone_filter = user.assigned_zone

    if zone_filter:
        active = [a for a in active if a.zone == zone_filter]

    total_active = len(active)
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    daily = db.query(Anomaly).filter(Anomaly.detected_at >= today).all()
    if zone_filter:
        daily = [a for a in daily if a.zone == zone_filter]
    total_daily_loss = sum(a.est_loss_litres for a in daily)

    zones = ["Zone A", "Zone B", "Zone C"]
    zone_nrw = {}
    for z in zones:
        z_anomalies = db.query(Anomaly).filter(Anomaly.zone == z, Anomaly.status.in_(["ACTIVE", "DISPATCHED"])).all()
        total_loss = sum(a.est_loss_litres for a in z_anomalies)
        estimated_supply = 50000.0
        zone_nrw[z] = round((total_loss / estimated_supply) * 100, 2) if estimated_supply > 0 else 0.0

    return KPIResponse(total_active_anomalies=total_active, total_daily_loss_litres=round(total_daily_loss, 1), zone_nrw=zone_nrw)


@router.get("/anomalies", response_model=List[AnomalyOut])
def get_active_anomalies(db: Session = Depends(get_db), user: User = Depends(all_roles)):
    query = db.query(Anomaly).filter(Anomaly.status.in_(["ACTIVE", "DISPATCHED"]))
    if user.role == "zone_engineer" and user.assigned_zone:
        query = query.filter(Anomaly.zone == user.assigned_zone)
    return query.order_by(Anomaly.detected_at.desc()).limit(100).all()
