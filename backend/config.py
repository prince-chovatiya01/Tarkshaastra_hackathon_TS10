# Configuration loader for Ghost Water Detector backend
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/water_network")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "hackathon-secret-key-change-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24
SIMULATION_INTERVAL_SECONDS = int(os.getenv("SIMULATION_INTERVAL_SECONDS", "3"))
MODEL_PATH = os.getenv("MODEL_PATH", "backend/data/classifier_model.json")
DATASET_PATH = os.getenv("DATASET_PATH", "backend/data/dataset.csv")
