# Dispatch router — crew list, dispatch work orders, Telegram notifications, timeout checker
import asyncio
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.database import get_db, SessionLocal
from backend.models import CrewMember, DispatchLog, Anomaly, User
from backend.schemas import CrewMemberOut, DispatchRequest, DispatchOut
from backend.auth import require_role
from backend.services.notification import send_notification, build_work_order_message
from backend.websocket_manager import manager

router = APIRouter(tags=["dispatch"])

engineer_only = require_role("zone_engineer")


@router.get("/api/crew", response_model=List[CrewMemberOut])
def list_crew(zone: Optional[str] = None, available: Optional[bool] = None, db: Session = Depends(get_db), user: User = Depends(engineer_only)):
    query = db.query(CrewMember)
    if zone:
        query = query.filter(CrewMember.zone == zone)
    if available is not None:
        query = query.filter(CrewMember.is_available == available)
    return query.all()


@router.put("/api/crew/{crew_id}/telegram")
def register_crew_telegram(crew_id: int, request_body: dict, db: Session = Depends(get_db)):
    crew = db.query(CrewMember).filter(CrewMember.id == crew_id).first()
    if not crew:
        raise HTTPException(status_code=404, detail="Crew member not found")
    crew.telegram_chat_id = request_body.get("chat_id", "")
    db.commit()
    return {"status": "ok", "crew_id": crew_id, "name": crew.name}


@router.post("/api/dispatch", response_model=DispatchOut)
async def create_dispatch(body: DispatchRequest, db: Session = Depends(get_db), user: User = Depends(engineer_only)):
    anomaly = db.query(Anomaly).filter(Anomaly.id == body.anomaly_id).first()
    if not anomaly:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Anomaly not found")
    if anomaly.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Anomaly is not in ACTIVE status")

    crew = db.query(CrewMember).filter(CrewMember.id == body.crew_member_id).first()
    if not crew:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crew member not found")
    if not crew.is_available:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Crew member is currently unavailable")

    dispatch = DispatchLog(
        anomaly_id=anomaly.id,
        segment_id=anomaly.segment_id,
        dispatched_by=user.id,
        crew_member_id=crew.id,
        zone=anomaly.zone,
        anomaly_type=anomaly.anomaly_type,
        urgency=anomaly.urgency,
        status="SENT",
        timeout_at=datetime.utcnow() + timedelta(hours=2),
    )
    db.add(dispatch)
    db.flush()

    crew.is_available = False
    crew.current_dispatch_id = dispatch.id
    anomaly.status = "DISPATCHED"
    db.commit()
    db.refresh(dispatch)

    message = build_work_order_message(
        wo_id=dispatch.id,
        anomaly_type=anomaly.anomaly_type,
        urgency=anomaly.urgency,
        segment_id=anomaly.segment_id,
        zone=anomaly.zone,
        lat=anomaly.lat,
        lng=anomaly.lng,
        est_loss=anomaly.est_loss_litres,
    )
    sid = send_notification(crew.telegram_chat_id or "", message)
    dispatch.message_sid = sid
    db.commit()
    db.refresh(dispatch)

    await manager.broadcast({
        "event": "dispatch_update",
        "data": {"anomaly_id": anomaly.id, "status": "DISPATCHED", "crew_member": crew.name, "dispatch_id": dispatch.id},
    })

    return dispatch


@router.post("/api/webhook/crew-response")
async def handle_crew_reply(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    body_text = data.get("response", "").strip().upper()
    crew_id = data.get("crew_id", None)
    from_phone = data.get("phone", "")

    valid_responses = {"DONE", "NOT_FOUND", "NO_ANOMALY"}
    if body_text not in valid_responses:
        return {"status": "ignored", "reason": "unrecognized reply"}

    if crew_id:
        crew = db.query(CrewMember).filter(CrewMember.id == crew_id).first()
    else:
        crew = db.query(CrewMember).filter(CrewMember.phone == from_phone).first()
    if not crew:
        return {"status": "ignored", "reason": "unknown crew member"}

    dispatch = db.query(DispatchLog).filter(
        DispatchLog.crew_member_id == crew.id,
        DispatchLog.status.in_(["SENT", "ACKNOWLEDGED", "IN_PROGRESS"]),
    ).order_by(DispatchLog.dispatched_at.desc()).first()
    if not dispatch:
        return {"status": "ignored", "reason": "no active dispatch"}

    anomaly = db.query(Anomaly).filter(Anomaly.id == dispatch.anomaly_id).first()

    response_map = {
        "DONE": ("DONE", "RESOLVED"),
        "NOT_FOUND": ("NOT_FOUND", "UNRESOLVED"),
        "NO_ANOMALY": ("NO_ANOMALY", "FALSE_ALARM"),
    }
    dispatch_status, anomaly_status = response_map[body_text]
    dispatch.status = dispatch_status
    dispatch.crew_response = body_text
    dispatch.resolved_at = datetime.utcnow()

    if anomaly:
        anomaly.status = anomaly_status
        if body_text == "NO_ANOMALY":
            anomaly.is_false_positive = True

    crew.is_available = True
    crew.current_dispatch_id = None
    db.commit()

    await manager.broadcast({
        "event": "status_update",
        "data": {
            "anomaly_id": dispatch.anomaly_id,
            "dispatch_id": dispatch.id,
            "status": anomaly_status,
            "crew_response": body_text,
        },
    })

    return {"status": "ok"}


async def run_timeout_checker():
    while True:
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            expired = db.query(DispatchLog).filter(
                DispatchLog.status.in_(["SENT", "ACKNOWLEDGED", "IN_PROGRESS"]),
                DispatchLog.timeout_at <= now,
            ).all()

            for dispatch in expired:
                dispatch.status = "TIMEOUT"
                dispatch.resolved_at = now

                crew = db.query(CrewMember).filter(CrewMember.id == dispatch.crew_member_id).first()
                if crew:
                    crew.is_available = True
                    crew.current_dispatch_id = None

                anomaly = db.query(Anomaly).filter(Anomaly.id == dispatch.anomaly_id).first()
                if anomaly:
                    anomaly.status = "ACTIVE"

                await manager.broadcast({
                    "event": "timeout",
                    "data": {"anomaly_id": dispatch.anomaly_id, "dispatch_id": dispatch.id, "status": "TIMEOUT"},
                })

            db.commit()
        except Exception as exc:
            print(f"[TIMEOUT CHECKER ERROR] {exc}")
            db.rollback()
        finally:
            db.close()

        await asyncio.sleep(60)
