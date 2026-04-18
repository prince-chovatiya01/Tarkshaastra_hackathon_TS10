# Notification service — Telegram Bot (free) with console mock fallback
import urllib.request
import urllib.parse
import json
from backend.config import TELEGRAM_BOT_TOKEN


def send_notification(chat_id: str, message: str) -> str:
    """Send a message via Telegram Bot API. Falls back to console mock if not configured."""
    if TELEGRAM_BOT_TOKEN and chat_id:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = json.dumps({
            "chat_id": chat_id,
            "text": message
        }).encode("utf-8")
        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=10)
            result = json.loads(resp.read())
            if result.get("ok"):
                msg_id = result["result"]["message_id"]
                print(f"[TELEGRAM OK] Message sent to chat_id={chat_id}, msg_id={msg_id}")
                return f"TELEGRAM_OK_{msg_id}"
            print(f"[TELEGRAM ERR] Response not OK: {result}")
            return "TELEGRAM_ERR"
        except urllib.error.HTTPError as http_err:
            error_body = http_err.read().decode("utf-8", errors="replace")
            print(f"[TELEGRAM ERROR] HTTP {http_err.code}: {error_body}")
            print(f"[TELEGRAM ERROR] chat_id was: '{chat_id}', token starts with: '{TELEGRAM_BOT_TOKEN[:10]}...'")
            return "TELEGRAM_FAILED"
        except Exception as exc:
            print(f"[TELEGRAM ERROR] {exc}")
            return "TELEGRAM_FAILED"
    if not TELEGRAM_BOT_TOKEN:
        print(f"[NOTIFICATION MOCK] No TELEGRAM_BOT_TOKEN set")
    if not chat_id:
        print(f"[NOTIFICATION MOCK] No chat_id for crew member — set it in Crew Keys panel")
    print(f"[NOTIFICATION MOCK] Message:\n{message}")
    return "MOCK_SID_000"


def build_work_order_message(wo_id: int, anomaly_type: str, urgency: str, segment_id: str, zone: str, lat: float, lng: float, est_loss: float) -> str:
    type_label = anomaly_type.upper().replace("_", " ")
    return (
        f"🚨 *WORK ORDER #{wo_id}*\n\n"
        f"*Type:* {type_label}\n"
        f"*Urgency:* {urgency}\n"
        f"*Segment:* {segment_id}, {zone}\n"
        f"📍 Location: https://maps.google.com/?q={lat},{lng}\n"
        f"💧 *Est. Loss:* {est_loss:.0f} L/day\n"
        f"\n"
        f"Reply with:\n"
        f"  DONE — if repaired\n"
        f"  NOT FOUND — if no anomaly at location\n"
        f"  NO ANOMALY — if false alarm"
    )
