# Analyst router — anomaly history, CSV export, false positive flagging
import csv
import io
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Anomaly, User
from backend.schemas import AnomalyOut
from backend.auth import require_role

router = APIRouter(tags=["analyst"])

analyst_only = require_role("data_analyst")


@router.get("/api/anomalies", response_model=List[AnomalyOut])
def get_anomalies(
    zone: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    anomaly_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(analyst_only),
):
    query = db.query(Anomaly)
    if zone:
        query = query.filter(Anomaly.zone == zone)
    if date_from:
        query = query.filter(Anomaly.detected_at >= date_from)
    if date_to:
        query = query.filter(Anomaly.detected_at <= date_to)
    if anomaly_type:
        query = query.filter(Anomaly.anomaly_type == anomaly_type)
    return query.order_by(Anomaly.detected_at.desc()).limit(500).all()


@router.get("/api/anomalies/export")
def export_csv(
    zone: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    anomaly_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(analyst_only),
):
    query = db.query(Anomaly)
    if zone:
        query = query.filter(Anomaly.zone == zone)
    if date_from:
        query = query.filter(Anomaly.detected_at >= date_from)
    if date_to:
        query = query.filter(Anomaly.detected_at <= date_to)
    if anomaly_type:
        query = query.filter(Anomaly.anomaly_type == anomaly_type)
    rows = query.order_by(Anomaly.detected_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "segment_id", "detected_at", "anomaly_type", "urgency", "confidence", "est_loss_litres", "zone", "lat", "lng", "status", "is_false_positive"])
    for r in rows:
        writer.writerow([r.id, r.segment_id, r.detected_at, r.anomaly_type, r.urgency, r.confidence, r.est_loss_litres, r.zone, r.lat, r.lng, r.status, r.is_false_positive])
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=anomalies_export.csv"},
    )


@router.put("/api/anomalies/{anomaly_id}/false-positive")
def flag_false_positive(anomaly_id: int, db: Session = Depends(get_db), user: User = Depends(analyst_only)):
    anomaly = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()
    if not anomaly:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anomaly not found")
    anomaly.is_false_positive = True
    anomaly.status = "FALSE_ALARM"
    db.commit()
    return {"status": "ok", "anomaly_id": anomaly_id}


@router.get("/api/stats/false-positive-rate")
def false_positive_rate(db: Session = Depends(get_db), user: User = Depends(analyst_only)):
    total = db.query(Anomaly).count()
    false_positives = db.query(Anomaly).filter(Anomaly.is_false_positive == True).count()
    rate = round((false_positives / total) * 100, 2) if total > 0 else 0.0
    return {"total": total, "false_positives": false_positives, "rate_percent": rate}
