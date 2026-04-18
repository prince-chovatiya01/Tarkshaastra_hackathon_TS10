# Training script - trains XGBoost classifier + regressor from the dataset
# Run: python -m backend.train_model
import os
import sys
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.ml_engine import (
    engineer_features, train_classifier, train_loss_regressor, save_models
)

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "dataset.csv")


def main():
    print("=" * 60)
    print("  GHOST WATER DETECTOR - NRW MODEL TRAINING")
    print("=" * 60)

    # 1. Load data
    print("\n[1/5] Loading dataset...")
    df = pd.read_excel(DATA_PATH)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(['sensor_id', 'timestamp']).reset_index(drop=True)
    print(f"  Loaded {len(df):,} records")
    print(f"  Columns: {list(df.columns)}")
    print(f"  NRW types: {df['nrw_type'].value_counts().to_dict()}")

    # 2. Feature engineering
    print("\n[2/5] Engineering features across 4 signature families...")
    df_feat = engineer_features(df)
    print(f"  Generated {len(df_feat.columns)} columns total")

    # 3. Train classifier
    print("\n[3/5] Training XGBoost NRW Classifier...")
    classifier, label_encoder, acc, report, feat_imp = train_classifier(df_feat)

    print(f"\n{'=' * 60}")
    print(f"  XGBOOST NRW CLASSIFIER RESULTS")
    print(f"{'=' * 60}")
    print(f"  Overall Accuracy : {acc * 100:.2f}%")
    print(f"{'=' * 60}")
    print(report)

    print("Top 10 Predictive Features:")
    for feat, imp in feat_imp.head(10).items():
        bar = "#" * int(imp * 100)
        print(f"  {feat:<30} {imp:.4f}  {bar}")

    # 4. Train loss regressor
    print("\n[4/5] Training XGBoost Loss Regressor...")
    regressor, mae, rmse, r2 = train_loss_regressor(df_feat)

    print(f"\n{'=' * 60}")
    print(f"  LOSS REGRESSION RESULTS")
    print(f"{'=' * 60}")
    print(f"  MAE : {mae:.2f}")
    print(f"  RMSE: {rmse:.2f}")
    print(f"  R2  : {r2:.4f}")
    print(f"{'=' * 60}")

    # 5. Save models
    print("\n[5/5] Saving models to disk...")
    save_models(classifier, regressor, label_encoder)

    print(f"\n{'=' * 60}")
    print("  TRAINING COMPLETE")
    print(f"  Classifier accuracy: {acc * 100:.2f}%")
    print(f"  Regressor R2 score:  {r2:.4f}")
    print(f"  Models saved. Restart uvicorn to use them.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
