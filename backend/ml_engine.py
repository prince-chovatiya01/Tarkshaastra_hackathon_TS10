# ML Engine - XGBoost NRW Classifier + Loss Regressor
# Integrated from ML_model_classify_v1.ipynb (unchanged model logic)
import os
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from xgboost import XGBClassifier, XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    classification_report, accuracy_score, confusion_matrix,
    mean_absolute_error, mean_squared_error, r2_score
)
import warnings
warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "data")
CLASSIFIER_PATH = os.path.join(MODEL_DIR, "classifier_model.pkl")
REGRESSOR_PATH = os.path.join(MODEL_DIR, "regressor_model.pkl")
ENCODER_PATH = os.path.join(MODEL_DIR, "label_encoder.pkl")

# Feature columns — exact match from notebook
FEATURE_COLS = [
    'pressure_bar', 'flow_lpm', 'expected_pressure_bar',
    'pressure_diff', 'pressure_ratio', 'pressure_drop_pct', 'pressure_abs_diff',
    'adj_pressure_ratio',
    'hour', 'day_of_week', 'demand_peak_flag',
    'p_rmean_5', 'p_rstd_5', 'p_rmean_10', 'p_rstd_10', 'p_rmean_30', 'p_rstd_30',
    'flow_rmean_10', 'flow_deviation',
    'flow_vs_zone_mean', 'zone_mean_flow', 'zone_mean_pressure',
    'estimated_loss_liters', 'loss_rmean_10', 'loss_vs_pressure', 'zone_total_loss',
    'burst_flag', 'seepage_flag', 'zone_enc'
]

# Loss regressor uses a subset (drops leaky columns)
LOSS_FEATURE_COLS = [c for c in FEATURE_COLS if c not in [
    'estimated_loss_liters', 'loss_vs_pressure', 'loss_rmean_10', 'zone_total_loss'
]]

# Urgency mapping
NRW_URGENCY = {
    'pipe_burst': 'High',
    'illegal_tap': 'Medium',
    'meter_tamper': 'Medium',
    'slow_seepage': 'Low',
    'none': 'Normal'
}

NRW_ACTION = {
    'pipe_burst': (
        'IMMEDIATE field dispatch required. Excavate segment and replace burst section. '
        'Shut valve upstream of segment. Estimated repair: 4-6 hours.'
    ),
    'illegal_tap': (
        'Inspect pipe segment for unauthorised connection. '
        'Photograph evidence. File FIR if confirmed. Seal tap.'
    ),
    'meter_tamper': (
        'Dispatch meter inspector. Compare meter reading to zone-level flow reconciliation. '
        'Replace meter if tampered. Issue notice to property owner.'
    ),
    'slow_seepage': (
        'Schedule non-urgent repair within 48 hours. '
        'Apply pipe repair clamp or replace segment section.'
    ),
    'none': 'No action required.'
}


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build 32 features across 4 families:
      1. Pressure Differential Signatures (PDS)
      2. Temporal Rolling Patterns
      3. Zone-Level Billing Reconciliation (for meter tamper)
      4. NRW Type Signature Flags
    """
    df = df.copy()

    # Family 1: Pressure Differential Signatures
    df['pressure_diff'] = df['expected_pressure_bar'] - df['pressure_bar']
    df['pressure_ratio'] = df['pressure_diff'] / df['expected_pressure_bar']
    df['pressure_drop_pct'] = df['pressure_ratio'] * 100
    df['pressure_abs_diff'] = df['pressure_diff'].abs()

    # Demand-peak adjusted ratio
    df['adj_pressure_ratio'] = np.where(
        df['demand_peak_flag'] == 1,
        df['pressure_ratio'] * 0.6,
        df['pressure_ratio']
    )

    # Family 2: Temporal Rolling Patterns
    for w in [5, 10, 30]:
        df[f'p_rmean_{w}'] = df.groupby('sensor_id')['pressure_bar'].transform(
            lambda x: x.rolling(w, min_periods=1).mean())
        df[f'p_rstd_{w}'] = df.groupby('sensor_id')['pressure_bar'].transform(
            lambda x: x.rolling(w, min_periods=1).std().fillna(0))
    df['flow_rmean_10'] = df.groupby('sensor_id')['flow_lpm'].transform(
        lambda x: x.rolling(10, min_periods=1).mean())
    df['flow_deviation'] = df['flow_lpm'] - df['flow_rmean_10']

    # Family 3: Zone-Level Billing Reconciliation
    df['date'] = df['timestamp'].dt.date
    zone_stats = df.groupby(['zone', 'date']).agg(
        zone_mean_flow=('flow_lpm', 'mean'),
        zone_mean_pressure=('pressure_bar', 'mean'),
        zone_total_loss=('estimated_loss_liters', 'sum')
    ).reset_index()
    df = df.merge(zone_stats, on=['zone', 'date'], how='left')
    df['flow_vs_zone_mean'] = df['flow_lpm'] - df['zone_mean_flow']

    df['loss_rmean_10'] = df.groupby('sensor_id')['estimated_loss_liters'].transform(
        lambda x: x.rolling(10, min_periods=1).mean())
    df['loss_vs_pressure'] = (
        df['estimated_loss_liters'] / (df['pressure_abs_diff'] + 0.01)
    )

    # Family 4: NRW Signature Flags
    df['burst_flag'] = (df['pressure_drop_pct'] > 40).astype(int)
    df['seepage_flag'] = (
        (df['pressure_drop_pct'] > 12) & (df['pressure_drop_pct'] <= 40)
    ).astype(int)

    # Time features
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['zone_enc'] = df['zone'].map({'Z1': 0, 'Z2': 1, 'Z3': 2})

    return df


def train_classifier(df: pd.DataFrame):
    """Train XGBoost NRW classifier. Returns (model, label_encoder, accuracy, report)."""
    X = df[FEATURE_COLS].fillna(0).values
    le = LabelEncoder()
    y = le.fit_transform(df['nrw_type'])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = XGBClassifier(
        n_estimators=300,
        max_depth=7,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        eval_metric='mlogloss',
        random_state=42,
        n_jobs=-1
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False
    )

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=le.classes_)

    # Feature importance
    feat_imp = pd.Series(
        model.feature_importances_, index=FEATURE_COLS
    ).sort_values(ascending=False)

    return model, le, acc, report, feat_imp


def train_loss_regressor(df: pd.DataFrame):
    """Train XGBoost loss regressor. Returns (model, mae, rmse, r2)."""
    y_loss = df['estimated_loss_liters'].values
    X_loss = df[LOSS_FEATURE_COLS].fillna(0).values

    X_train, X_test, y_train, y_test = train_test_split(
        X_loss, y_loss, test_size=0.2, random_state=42
    )

    model = XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    return model, mae, rmse, r2


def save_models(classifier, regressor, label_encoder):
    """Persist trained models to disk."""
    with open(CLASSIFIER_PATH, 'wb') as f:
        pickle.dump(classifier, f)
    with open(REGRESSOR_PATH, 'wb') as f:
        pickle.dump(regressor, f)
    with open(ENCODER_PATH, 'wb') as f:
        pickle.dump(label_encoder, f)
    print(f"[ML] Models saved to {MODEL_DIR}")


def load_models():
    """Load persisted models from disk."""
    with open(CLASSIFIER_PATH, 'rb') as f:
        classifier = pickle.load(f)
    with open(REGRESSOR_PATH, 'rb') as f:
        regressor = pickle.load(f)
    with open(ENCODER_PATH, 'rb') as f:
        label_encoder = pickle.load(f)
    return classifier, regressor, label_encoder


class MLEngine:
    """Production inference engine wrapping the trained XGBoost models."""

    def __init__(self):
        self.classifier = None
        self.regressor = None
        self.label_encoder = None
        self.is_loaded = False

        if os.path.exists(CLASSIFIER_PATH) and os.path.exists(REGRESSOR_PATH):
            try:
                self.classifier, self.regressor, self.label_encoder = load_models()
                self.is_loaded = True
                print("[ML] Loaded trained models from disk")
            except Exception as exc:
                print(f"[ML] Failed to load models: {exc}")

    def predict(self, features: dict, timestamp: datetime = None) -> dict:
        """
        Predict anomaly type from a single sensor reading.
        features must include: pressure_bar, flow_lpm, expected_pressure_bar,
                               demand_peak_flag, estimated_loss_liters
        """
        if not self.is_loaded:
            return self._mock_predict(features, timestamp)

        ts = timestamp or datetime.utcnow()
        is_peak = features.get("is_peak_hour", False)

        # Build a single-row dataframe with raw features
        row = {
            'pressure_bar': features.get('pressure_value', features.get('pressure_bar', 3.5)),
            'flow_lpm': features.get('flow_rate', features.get('flow_lpm', 30.0)),
            'expected_pressure_bar': features.get('expected_pressure_bar', 3.5),
            'demand_peak_flag': 1 if is_peak else 0,
            'estimated_loss_liters': features.get('estimated_loss_liters', 0),
            'sensor_id': features.get('sensor_id', 'LIVE'),
            'zone': features.get('zone', 'Z1'),
            'timestamp': ts,
        }
        df_single = pd.DataFrame([row])
        df_single['timestamp'] = pd.to_datetime(df_single['timestamp'])

        # Compute derived features inline (no rolling available for single row)
        p_diff = row['expected_pressure_bar'] - row['pressure_bar']
        p_ratio = p_diff / (row['expected_pressure_bar'] + 0.001)
        p_drop_pct = p_ratio * 100
        p_abs = abs(p_diff)
        adj_ratio = p_ratio * 0.6 if row['demand_peak_flag'] == 1 else p_ratio
        loss = row['estimated_loss_liters']

        feat_row = {
            'pressure_bar': row['pressure_bar'],
            'flow_lpm': row['flow_lpm'],
            'expected_pressure_bar': row['expected_pressure_bar'],
            'pressure_diff': p_diff,
            'pressure_ratio': p_ratio,
            'pressure_drop_pct': p_drop_pct,
            'pressure_abs_diff': p_abs,
            'adj_pressure_ratio': adj_ratio,
            'hour': ts.hour,
            'day_of_week': ts.weekday(),
            'demand_peak_flag': row['demand_peak_flag'],
            'p_rmean_5': row['pressure_bar'],
            'p_rstd_5': 0.0,
            'p_rmean_10': row['pressure_bar'],
            'p_rstd_10': 0.0,
            'p_rmean_30': row['pressure_bar'],
            'p_rstd_30': 0.0,
            'flow_rmean_10': row['flow_lpm'],
            'flow_deviation': 0.0,
            'flow_vs_zone_mean': 0.0,
            'zone_mean_flow': row['flow_lpm'],
            'zone_mean_pressure': row['pressure_bar'],
            'estimated_loss_liters': loss,
            'loss_rmean_10': loss,
            'loss_vs_pressure': loss / (p_abs + 0.01),
            'zone_total_loss': loss,
            'burst_flag': 1 if p_drop_pct > 40 else 0,
            'seepage_flag': 1 if 12 < p_drop_pct <= 40 else 0,
            'zone_enc': {'Z1': 0, 'Z2': 1, 'Z3': 2}.get(row['zone'], 0),
        }

        X = np.array([[feat_row[c] for c in FEATURE_COLS]])
        pred_class = self.classifier.predict(X)[0]
        proba = self.classifier.predict_proba(X)[0]
        confidence = float(proba.max())
        anomaly_type = self.label_encoder.inverse_transform([pred_class])[0]

        if anomaly_type == 'none':
            return {"type": "normal", "confidence": confidence, "urgency": "Normal", "est_loss_litres": 0}

        # Predict loss with regressor
        X_loss = np.array([[feat_row[c] for c in LOSS_FEATURE_COLS]])
        est_loss = float(self.regressor.predict(X_loss)[0])
        est_loss = max(0, est_loss)

        # Map notebook NRW types to our dashboard types
        type_map = {
            'pipe_burst': 'pipe_burst',
            'slow_seepage': 'slow_seepage',
            'illegal_tap': 'illegal_tap',
            'meter_tamper': 'illegal_tap',
        }
        dashboard_type = type_map.get(anomaly_type, anomaly_type)
        urgency = NRW_URGENCY.get(anomaly_type, 'Low')

        return {
            "type": dashboard_type,
            "confidence": round(confidence, 4),
            "urgency": urgency,
            "est_loss_litres": round(est_loss, 1),
        }

    def _mock_predict(self, features: dict, timestamp: datetime = None) -> dict:
        """Fallback mock predictor when models are not trained yet."""
        import random
        ts = timestamp or datetime.utcnow()
        if 6 <= ts.hour <= 9:
            if random.random() < 0.85:
                return {"type": "normal", "confidence": 0.0, "urgency": "Normal", "est_loss_litres": 0}

        roll = random.random()
        if roll < 0.70:
            return {"type": "normal", "confidence": 0.0, "urgency": "Normal", "est_loss_litres": 0}

        types = ["pipe_burst", "slow_seepage", "illegal_tap"]
        weights = [0.3, 0.4, 0.3]
        chosen = random.choices(types, weights=weights, k=1)[0]
        confidence = round(random.uniform(0.65, 0.98), 4)

        loss_ranges = {"pipe_burst": (2000, 5000), "slow_seepage": (200, 1500), "illegal_tap": (500, 3000)}
        lo, hi = loss_ranges[chosen]
        est_loss = round(random.uniform(lo, hi), 1)

        urgency_map = {"pipe_burst": "High", "slow_seepage": "Low", "illegal_tap": "Medium"}

        return {
            "type": chosen,
            "confidence": confidence,
            "urgency": urgency_map[chosen],
            "est_loss_litres": est_loss,
        }
