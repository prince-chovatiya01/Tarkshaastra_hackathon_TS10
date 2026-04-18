# Simulator — generates mock sensor readings, runs ML prediction, writes to DB and broadcasts via WebSocket
import asyncio
import random
from datetime import datetime
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import SensorReading, Anomaly, PipeSegment
from backend.ml_engine import MLEngine
from backend.websocket_manager import manager
from backend.config import SIMULATION_INTERVAL_SECONDS

ml = MLEngine()

ZONE_SEGMENTS = {
    "Zone A": [f"ZA-SEG-{str(i).zfill(3)}" for i in range(1, 21)],
    "Zone B": [f"ZB-SEG-{str(i).zfill(3)}" for i in range(1, 21)],
    "Zone C": [f"ZC-SEG-{str(i).zfill(3)}" for i in range(1, 21)],
}

ALL_SEGMENTS = []
for zone, segs in ZONE_SEGMENTS.items():
    for seg in segs:
        ALL_SEGMENTS.append((seg, zone))

segment_index = 0


def generate_mock_reading(segment_id: str, zone: str) -> dict:
    # MOCK: replace with CSV reader
    now = datetime.utcnow()
    base_pressure = random.uniform(2.5, 5.0)
    flow_rate = random.uniform(10.0, 60.0)
    is_peak = 6 <= now.hour <= 9
    return {
        "segment_id": segment_id,
        "zone": zone,
        "timestamp": now,
        "pressure_value": round(base_pressure, 2),
        "flow_rate": round(flow_rate, 2),
        "is_peak_hour": is_peak,
    }


def get_segment_coords(db: Session, segment_id: str) -> tuple:
    seg = db.query(PipeSegment).filter(PipeSegment.segment_id == segment_id).first()
    if seg and seg.geom is not None:
        from geoalchemy2.shape import to_shape
        line = to_shape(seg.geom)
        midpoint = line.interpolate(0.5, normalized=True)
        return (midpoint.y, midpoint.x)
    zone_prefix = segment_id[:2]
    fallback = {
        "ZA": (23.0350, 72.5600),
        "ZB": (23.0200, 72.5200),
        "ZC": (22.9700, 72.4800),
    }
    base = fallback.get(zone_prefix, (23.0225, 72.5714))
    return (base[0] + random.uniform(-0.005, 0.005), base[1] + random.uniform(-0.005, 0.005))


async def run_simulator():
    global segment_index
    while True:
        db = SessionLocal()
        try:
            seg_id, zone = ALL_SEGMENTS[segment_index % len(ALL_SEGMENTS)]
            segment_index += 1

            reading_data = generate_mock_reading(seg_id, zone)

            sensor = SensorReading(
                segment_id=reading_data["segment_id"],
                timestamp=reading_data["timestamp"],
                pressure_value=reading_data["pressure_value"],
                flow_rate=reading_data["flow_rate"],
                is_peak_hour=reading_data["is_peak_hour"],
            )
            db.add(sensor)
            db.commit()

            features = {
                "pressure_value": reading_data["pressure_value"],
                "flow_rate": reading_data["flow_rate"],
                "is_peak_hour": reading_data["is_peak_hour"],
            }
            result = ml.predict(features, reading_data["timestamp"])

            if result["type"] != "normal":
                lat, lng = get_segment_coords(db, seg_id)
                anomaly = Anomaly(
                    segment_id=seg_id,
                    anomaly_type=result["type"],
                    urgency=result["urgency"],
                    confidence=result["confidence"],
                    est_loss_litres=result["est_loss_litres"],
                    zone=zone,
                    lat=lat,
                    lng=lng,
                    status="ACTIVE",
                )
                db.add(anomaly)
                db.commit()
                db.refresh(anomaly)

                ws_payload = {
                    "event": "new_anomaly",
                    "data": {
                        "id": anomaly.id,
                        "segment_id": seg_id,
                        "anomaly_type": result["type"],
                        "urgency": result["urgency"],
                        "confidence": result["confidence"],
                        "est_loss_litres": result["est_loss_litres"],
                        "zone": zone,
                        "lat": lat,
                        "lng": lng,
                        "status": "ACTIVE",
                        "detected_at": str(anomaly.detected_at),
                    },
                }
                await manager.broadcast(ws_payload)
        except Exception as exc:
            print(f"[SIMULATOR ERROR] {exc}")
            db.rollback()
        finally:
            db.close()

        await asyncio.sleep(SIMULATION_INTERVAL_SECONDS)
