# Twilio WhatsApp notification service
from backend.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM


def send_whatsapp(phone: str, message: str) -> str:
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            body=message,
            from_=TWILIO_WHATSAPP_FROM,
            to=f"whatsapp:{phone}",
        )
        return msg.sid
    print(f"[TWILIO MOCK] To: {phone}")
    print(f"[TWILIO MOCK] Message:\n{message}")
    return "MOCK_SID_000"


def build_work_order_message(wo_id: int, anomaly_type: str, urgency: str, segment_id: str, zone: str, lat: float, lng: float, est_loss: float) -> str:
    type_label = anomaly_type.upper().replace("_", " ")
    return (
        f"[ALERT] WORK ORDER #WO-{wo_id}\n"
        f"Type: {type_label}\n"
        f"Urgency: {urgency}\n"
        f"Segment: {segment_id}, {zone}\n"
        f"[LOCATION] Map: https://maps.google.com/?q={lat},{lng}\n"
        f"Est. Loss: {est_loss} L/day\n"
        f"\n"
        f"Reply:\n"
        f"  DONE - if repaired\n"
        f"  NOT_FOUND - if no anomaly at location\n"
        f"  NO_ANOMALY - if false alarm"
    )
