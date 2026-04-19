# Telegram Poller — background task that polls for crew replies via Telegram Bot API
import asyncio
import json
import urllib.request
from datetime import datetime
from backend.config import TELEGRAM_BOT_TOKEN
from backend.database import SessionLocal
from backend.models import CrewMember, DispatchLog, Anomaly
from backend.websocket_manager import manager

# Track the last processed update_id so we don't re-process old messages
_last_update_id = 0

# Map of accepted reply keywords to (dispatch_status, anomaly_status)
RESPONSE_MAP = {
    "DONE": ("DONE", "RESOLVED"),
    "NOT FOUND": ("NOT_FOUND", "UNRESOLVED"),
    "NOT_FOUND": ("NOT_FOUND", "UNRESOLVED"),
    "NO ANOMALY": ("NO_ANOMALY", "FALSE_ALARM"),
    "NO_ANOMALY": ("NO_ANOMALY", "FALSE_ALARM"),
}


def _get_updates(offset: int = 0) -> list:
    """Fetch new messages from Telegram Bot API."""
    if not TELEGRAM_BOT_TOKEN:
        return []
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?timeout=5&offset={offset}"
    try:
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        if data.get("ok"):
            return data.get("result", [])
    except Exception as exc:
        print(f"[TELEGRAM POLL ERROR] {exc}")
    return []


def _send_reply(chat_id: str, text: str):
    """Send a confirmation reply back to the crew member."""
    if not TELEGRAM_BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as exc:
        print(f"[TELEGRAM REPLY ERROR] {exc}")


async def process_crew_reply(chat_id: str, text: str):
    """Process a crew member's reply and update dispatch/anomaly status."""
    normalized = text.strip().upper()

    # Check if this is a valid response
    if normalized not in RESPONSE_MAP:
        return

    dispatch_status, anomaly_status = RESPONSE_MAP[normalized]

    db = SessionLocal()
    try:
        # Find crew member by telegram_chat_id
        crew = db.query(CrewMember).filter(CrewMember.telegram_chat_id == str(chat_id)).first()
        if not crew:
            _send_reply(chat_id, "⚠️ Your Telegram ID is not registered in the system. Contact your zone engineer.")
            return

        # Find their active dispatch
        dispatch = db.query(DispatchLog).filter(
            DispatchLog.crew_member_id == crew.id,
            DispatchLog.status.in_(["SENT", "ACKNOWLEDGED", "IN_PROGRESS"]),
        ).order_by(DispatchLog.dispatched_at.desc()).first()

        if not dispatch:
            _send_reply(chat_id, "ℹ️ No active work order found for you.")
            return

        # Update dispatch
        dispatch.status = dispatch_status
        dispatch.crew_response = normalized
        dispatch.resolved_at = datetime.utcnow()

        # Update anomaly
        anomaly = db.query(Anomaly).filter(Anomaly.id == dispatch.anomaly_id).first()
        if anomaly:
            anomaly.status = anomaly_status
            if normalized in ("NO ANOMALY", "NO_ANOMALY"):
                anomaly.is_false_positive = True

        # Make crew available again
        crew.is_available = True
        crew.current_dispatch_id = None
        db.commit()

        # Send confirmation to crew member
        confirmations = {
            "DONE": f"✅ Work Order #{dispatch.id} marked as RESOLVED. Thank you, {crew.name}! You are now available for new dispatches.",
            "NO_ANOMALY": f"📋 Work Order #{dispatch.id} marked as FALSE ALARM. You are now available.",
        }
        _send_reply(chat_id, confirmations.get(dispatch_status, "Response recorded."))

        # Broadcast to dashboard via WebSocket
        await manager.broadcast({
            "event": "status_update",
            "data": {
                "anomaly_id": dispatch.anomaly_id,
                "dispatch_id": dispatch.id,
                "status": anomaly_status,
                "crew_response": normalized,
                "crew_name": crew.name,
            },
        })

        print(f"[TELEGRAM POLL] Crew '{crew.name}' replied '{normalized}' for WO#{dispatch.id} → {anomaly_status}")

    except Exception as exc:
        print(f"[TELEGRAM POLL ERROR] {exc}")
        db.rollback()
    finally:
        db.close()


async def run_telegram_poller():
    """Background task that polls Telegram for crew replies every 10 seconds."""
    global _last_update_id

    if not TELEGRAM_BOT_TOKEN:
        print("[TELEGRAM POLL] No bot token configured, poller disabled")
        return

    print("[TELEGRAM POLL] Started — listening for crew replies...")

    # Initial fetch to get current offset (skip old messages)
    updates = _get_updates(0)
    if updates:
        _last_update_id = updates[-1]["update_id"] + 1

    while True:
        try:
            updates = _get_updates(_last_update_id)
            for update in updates:
                _last_update_id = update["update_id"] + 1
                msg = update.get("message", {})
                chat_id = msg.get("chat", {}).get("id")
                text = msg.get("text", "")
                if chat_id and text:
                    await process_crew_reply(str(chat_id), text)
        except Exception as exc:
            print(f"[TELEGRAM POLL ERROR] {exc}")

        await asyncio.sleep(10)
