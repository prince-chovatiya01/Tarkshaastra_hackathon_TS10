# ML Engine — mock implementation until real XGBoost models are plugged in
import random
from datetime import datetime

CLASS_LABELS = ["normal", "pipe_burst", "slow_seepage", "illegal_tap"]

LOSS_RANGES = {
    "pipe_burst": (2000, 5000),
    "slow_seepage": (100, 500),
    "illegal_tap": (500, 2000),
}

URGENCY_MAP = {
    "pipe_burst": lambda c: "Critical" if c > 0.9 else "High",
    "slow_seepage": lambda c: "Medium" if c > 0.8 else "Low",
    "illegal_tap": lambda c: "High" if c > 0.85 else "Medium",
}


class MLEngine:
    def __init__(self, classifier_path: str = None, regressor_path: str = None):
        self.classifier_path = classifier_path
        self.regressor_path = regressor_path

    def predict(self, features_dict: dict, timestamp: datetime) -> dict:
        is_peak = 6 <= timestamp.hour <= 9
        # MOCK: replace with real model
        roll = random.random()
        if roll < 0.70:
            anomaly_type = "normal"
        elif roll < 0.80:
            anomaly_type = "pipe_burst"
        elif roll < 0.90:
            anomaly_type = "slow_seepage"
        else:
            anomaly_type = "illegal_tap"

        # MOCK: replace with real model
        confidence = round(random.uniform(0.55, 0.99), 3)

        if is_peak and confidence < 0.85:
            return {"type": "normal", "confidence": confidence, "suppressed": True}

        if anomaly_type == "normal":
            return {"type": "normal", "confidence": confidence}

        # MOCK: replace with real model
        lo, hi = LOSS_RANGES[anomaly_type]
        est_loss_litres = round(random.uniform(lo, hi), 1)
        urgency = self._compute_urgency(anomaly_type, confidence)

        return {
            "type": anomaly_type,
            "confidence": confidence,
            "urgency": urgency,
            "est_loss_litres": est_loss_litres,
        }

    def _compute_urgency(self, anomaly_type: str, confidence: float) -> str:
        return URGENCY_MAP.get(anomaly_type, lambda c: "Low")(confidence)
