# FastAPI application entry point — mounts all routers, seeds database, starts simulator
import asyncio
import json
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import inspect
from backend.database import engine, Base, SessionLocal
from backend.models import User, CrewMember, Zone, PipeSegment, Anomaly, SensorReading, DispatchLog
from backend.auth import hash_password
from backend.websocket_manager import manager
from backend.routers import auth_router, dashboard, dispatch, analyst
from backend.simulator import run_simulator

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")


def seed_users(db):
    if db.query(User).count() > 0:
        return
    users = [
        User(username="manager", password_hash=hash_password("manager123"), full_name="Rajesh Patel", role="utility_manager"),
        User(username="engineer_a", password_hash=hash_password("engineer123"), full_name="Amit Shah", role="zone_engineer", assigned_zone="Zone A"),
        User(username="engineer_b", password_hash=hash_password("engineer123"), full_name="Priya Desai", role="zone_engineer", assigned_zone="Zone B"),
        User(username="engineer_c", password_hash=hash_password("engineer123"), full_name="Vikram Mehta", role="zone_engineer", assigned_zone="Zone C"),
        User(username="analyst", password_hash=hash_password("analyst123"), full_name="Neha Sharma", role="data_analyst"),
    ]
    db.add_all(users)
    db.commit()


def seed_crew(db):
    if db.query(CrewMember).count() > 0:
        return
    crew = [
        CrewMember(name="Suresh Kumar", phone="+919876543210", zone="Zone A"),
        CrewMember(name="Mahesh Joshi", phone="+919876543211", zone="Zone A"),
        CrewMember(name="Rakesh Patel", phone="+919876543212", zone="Zone B"),
        CrewMember(name="Dinesh Rao", phone="+919876543213", zone="Zone B"),
        CrewMember(name="Ganesh Tiwari", phone="+919876543214", zone="Zone C"),
        CrewMember(name="Ramesh Verma", phone="+919876543215", zone="Zone C"),
    ]
    db.add_all(crew)
    db.commit()


def reset_runtime_data(db):
    """Clear old anomalies and sensor readings on restart so we start fresh from real dataset."""
    db.query(DispatchLog).delete()
    db.query(Anomaly).delete()
    db.query(SensorReading).delete()
    # Reset crew availability
    for crew in db.query(CrewMember).all():
        crew.is_available = True
        crew.current_dispatch_id = None
    db.commit()
    print("[STARTUP] Cleared old anomalies, readings, and dispatches. Starting fresh.")


def load_geojson(db):
    if db.query(Zone).count() > 0 and db.query(PipeSegment).count() > 0:
        return

    # Clear existing geo data to reload from updated GeoJSON
    db.query(PipeSegment).delete()
    db.query(Zone).delete()
    db.commit()

    zones_path = os.path.join(DATA_DIR, "zones.geojson")
    if os.path.exists(zones_path):
        with open(zones_path, "r") as f:
            zones_data = json.load(f)
        for feature in zones_data.get("features", []):
            props = feature.get("properties", {})
            from geoalchemy2.elements import WKTElement
            from shapely.geometry import shape
            shapely_geom = shape(feature["geometry"])
            zone = Zone(zone_name=props.get("zone_name", "Unknown"))
            zone.geom = WKTElement(shapely_geom.wkt, srid=4326)
            db.add(zone)
        db.commit()
        print(f"[STARTUP] Loaded {len(zones_data.get('features', []))} zones")

    pipes_path = os.path.join(DATA_DIR, "pipe_segments.geojson")
    if os.path.exists(pipes_path):
        with open(pipes_path, "r") as f:
            pipes_data = json.load(f)
        for feature in pipes_data.get("features", []):
            props = feature.get("properties", {})
            from geoalchemy2.elements import WKTElement
            from shapely.geometry import shape
            shapely_geom = shape(feature["geometry"])
            seg = PipeSegment(
                segment_id=props.get("segment_id"),
                zone=props.get("zone"),
                ward_name=props.get("ward_name", ""),
                length_m=50.0,
            )
            seg.geom = WKTElement(shapely_geom.wkt, srid=4326)
            db.add(seg)
        db.commit()
        print(f"[STARTUP] Loaded {len(pipes_data.get('features', []))} pipe segments")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_users(db)
        seed_crew(db)
        load_geojson(db)
        reset_runtime_data(db)
    finally:
        db.close()
    simulator_task = asyncio.create_task(run_simulator())
    timeout_task = asyncio.create_task(dispatch.run_timeout_checker())
    yield
    simulator_task.cancel()
    timeout_task.cancel()


app = FastAPI(title="Ghost Water Detector", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(dashboard.router)
app.include_router(dispatch.router)
app.include_router(analyst.router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if os.path.isdir(os.path.join(FRONTEND_DIR, "stitch-components")):
    app.mount("/stitch-components", StaticFiles(directory=os.path.join(FRONTEND_DIR, "stitch-components")), name="stitch-components")

if os.path.isdir(os.path.join(DATA_DIR)):
    app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/dashboard")
def serve_dashboard():
    return FileResponse(os.path.join(FRONTEND_DIR, "dashboard.html"))
