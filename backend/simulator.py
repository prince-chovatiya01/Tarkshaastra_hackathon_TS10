# Simulator — cycles through real dataset records, runs ML prediction, writes to DB and broadcasts via WebSocket
import asyncio
import os
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import SensorReading, Anomaly
from backend.ml_engine import MLEngine
from backend.websocket_manager import manager
from backend.config import SIMULATION_INTERVAL_SECONDS

ml = MLEngine()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "dataset.csv")

ZONE_MAP = {"Z1": "Zone A", "Z2": "Zone B", "Z3": "Zone C"}

# Load dataset once at module level
_dataset = None
_index = 0


def _load_dataset():
    global _dataset
    if _dataset is not None:
        return _dataset
    df = pd.read_excel(DATA_PATH)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(["sensor_id", "timestamp"]).reset_index(drop=True)
    # Only keep anomaly rows for the simulator (to show interesting data)
    # But also sprinkle in normal rows
    anomaly_rows = df[df["nrw_type"] != "none"]
    normal_sample = df[df["nrw_type"] == "none"].sample(n=min(2000, len(df[df["nrw_type"] == "none"])), random_state=42)
    _dataset = pd.concat([anomaly_rows, normal_sample]).sample(frac=1, random_state=42).reset_index(drop=True)
    print(f"[SIMULATOR] Loaded {len(_dataset)} records from dataset ({len(anomaly_rows)} anomalies + {len(normal_sample)} normal)")
    return _dataset


async def run_simulator():
    global _index
    df = _load_dataset()

    while True:
        db = SessionLocal()
        try:
            row = df.iloc[_index % len(df)]
            _index += 1

            zone = ZONE_MAP.get(row["zone"], row["zone"])
            seg_id = row["segment_id"]
            lat = float(row["latitude"])
            lng = float(row["longitude"])
            now = datetime.utcnow()

            # Write sensor reading
            sensor = SensorReading(
                segment_id=seg_id,
                timestamp=now,
                pressure_value=float(row["pressure_bar"]),
                flow_rate=float(row["flow_lpm"]),
                is_peak_hour=bool(row["demand_peak_flag"]),
            )
            db.add(sensor)
            db.commit()

            # Run ML prediction
            features = {
                "pressure_value": float(row["pressure_bar"]),
                "flow_rate": float(row["flow_lpm"]),
                "expected_pressure_bar": float(row["expected_pressure_bar"]),
                "is_peak_hour": bool(row["demand_peak_flag"]),
                "estimated_loss_liters": float(row["estimated_loss_liters"]),
                "zone": row["zone"],
                "sensor_id": row["sensor_id"],
            }
            result = ml.predict(features, now)

            if result["type"] != "normal":
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
