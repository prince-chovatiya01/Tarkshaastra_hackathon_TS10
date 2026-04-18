# Ghost Water Detector

Real-time water network anomaly detection dashboard for Ahmedabad Municipal Corporation.

## Overview

Detects non-revenue water loss (pipe bursts, slow seepage, illegal taps) across 3 zones in Ahmedabad, localises anomalies to 50m pipe segments on a real map, and dispatches WhatsApp work orders to field crews.

## Setup

### Prerequisites
- Docker and Docker Compose
- Python 3.10+

### 1. Start Database
```bash
docker-compose up -d
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Application
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Open Dashboard
Navigate to `http://localhost:8000`

## Default Credentials

| Username | Password | Role |
|----------|----------|------|
| manager | manager123 | Utility Manager |
| engineer_a | engineer123 | Zone Engineer (Zone A) |
| engineer_b | engineer123 | Zone Engineer (Zone B) |
| engineer_c | engineer123 | Zone Engineer (Zone C) |
| analyst | analyst123 | Data Analyst |

## Architecture

- **Backend:** FastAPI + SQLAlchemy + GeoAlchemy2
- **Database:** PostgreSQL + PostGIS
- **Frontend:** Vanilla HTML/CSS/JS + Leaflet.js + Chart.js
- **Real-time:** WebSocket broadcast
- **Notifications:** Twilio WhatsApp API
- **ML:** XGBoost classifier + regressor (mock until models provided)

## API Endpoints

| Method | Path | Description | Role |
|--------|------|-------------|------|
| POST | /api/auth/login | Login | Public |
| GET | /api/auth/me | Current user | All |
| GET | /api/dashboard/kpis | KPI metrics | All |
| GET | /api/dashboard/anomalies | Active anomalies | All |
| GET | /api/crew | List crew members | Engineer |
| POST | /api/dispatch | Dispatch work order | Engineer |
| POST | /api/webhook/twilio | Twilio webhook | Public |
| GET | /api/anomalies | Query anomaly history | Analyst |
| GET | /api/anomalies/export | Export CSV | Analyst |
| PUT | /api/anomalies/{id}/false-positive | Flag false positive | Analyst |
| GET | /api/stats/false-positive-rate | FP rate stat | Analyst |