"""ML Platform Pipeline — end-to-end lifecycle demo.

Orchestrates: data generation → validation → feature engineering →
training (two models) → evaluation → champion selection → model registration.

Output:
  ml_platform/demo/results/metrics.json
  ml_platform/demo/results/validation_report.json
  ml_platform/demo/results/model_registry/<version>/
"""

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ds_tools" / "src"))
from ds_tools.evaluation.report import ClassificationEvaluator
from ds_tools.preprocessing.transformers import FrequencyEncoder

RESULTS_DIR = Path(__file__).parent / "results"
REGISTRY_DIR = RESULTS_DIR / "model_registry"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def calculate_psi(expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
    """Calculates Population Stability Index (PSI) to detect feature-level drift."""
    expected_percents = np.histogram(expected, bins=buckets)[0] / len(expected)
    actual_percents = np.histogram(actual, bins=buckets)[0] / len(actual)

    # Handle zero-counts with small epsilon
    expected_percents = np.clip(expected_percents, 1e-6, 1.0)
    actual_percents = np.clip(actual_percents, 1e-6, 1.0)

    psi_value = np.sum((expected_percents - actual_percents) * np.log(expected_percents / actual_percents))
    return float(psi_value)

# ---------------------------------------------------------------------------
# Step 1: Data generation
# ---------------------------------------------------------------------------


def generate_data(n: int = 10_000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.RandomState(seed)
    fraud_rate = 0.05
    n_fraud = int(n * fraud_rate)
    labels = np.array([0] * (n - n_fraud) + [1] * n_fraud)
    rng.shuffle(labels)

    amount = np.where(
        labels,
        rng.lognormal(6.5, 0.8, n),
        rng.lognormal(4.5, 1.0, n),
    )
    df = pd.DataFrame(
        {
            "transaction_amount": np.round(amount, 2),
            "hour_of_day": rng.choice(24, n),
            "day_of_week": rng.randint(0, 7, n),
            "merchant_id": rng.choice(["merch_" + str(i) for i in range(200)], n),
            "device_type": rng.choice(["mobile", "desktop", "tablet"], n, p=[0.6, 0.3, 0.1]),
            "is_international": rng.binomial(1, np.where(labels, 0.3, 0.05)),
            "old_balance": np.round(rng.exponential(5000, n), 2),
            "is_fraud": labels,
        }
    )
    df["new_balance"] = np.where(
        labels,
        df["old_balance"] * rng.uniform(0.0, 0.1, n),
        np.maximum(df["old_balance"] - df["transaction_amount"], 0),
    ).round(2)
    return df


# ---------------------------------------------------------------------------
# Step 2: Data validation
# ---------------------------------------------------------------------------


def validate_data(df: pd.DataFrame) -> dict:
    checks = []

    # Schema check
    required = ["transaction_amount", "hour_of_day", "merchant_id", "is_fraud"]
    missing_cols = [c for c in required if c not in df.columns]
    checks.append(
        {
            "check": "required_columns",
            "status": "PASS" if not missing_cols else "FAIL",
            "detail": f"missing: {missing_cols}" if missing_cols else "all present",
        }
    )

    # Row count
    checks.append(
        {
            "check": "row_count",
            "status": "PASS" if len(df) >= 1000 else "FAIL",
            "detail": f"{len(df)} rows",
        }
    )

    # Label distribution
    fraud_pct = df["is_fraud"].mean()
    checks.append(
        {
            "check": "label_distribution",
            "status": "PASS" if 0.01 < fraud_pct < 0.20 else "WARN",
            "detail": f"{fraud_pct:.2%} fraud",
        }
    )

    # Nulls check
    null_cols = df.columns[df.isnull().any()].tolist()
    checks.append(
        {
            "check": "null_values",
            "status": "PASS" if not null_cols else "WARN",
            "detail": f"nulls in: {null_cols}" if null_cols else "no nulls",
        }
    )

    # Amount distribution
    checks.append(
        {
            "check": "amount_range",
            "status": "PASS" if df["transaction_amount"].min() > 0 else "FAIL",
            "detail": f"min={df['transaction_amount'].min():.2f}, max={df['transaction_amount'].max():.2f}",
        }
    )

    # Drift check (PSI)
    # Simulate historical distribution as mean-centered Gaussian
    hist_amount = np.random.lognormal(4.5, 1.0, 1000)
    psi = calculate_psi(hist_amount, df["transaction_amount"].values)
    checks.append(
        {
            "check": "data_drift_psi",
            "status": "PASS" if psi < 0.2 else "WARN",
            "detail": f"psi={psi:.4f} (threshold=0.2)",
        }
    )

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rows": len(df),
        "columns": len(df.columns),
        "checks": checks,
        "overall": "PASS" if all(c["status"] != "FAIL" for c in checks) else "FAIL",
    }

    passed = sum(1 for c in checks if c["status"] == "PASS")
    print(f"  Validation: {passed}/{len(checks)} checks passed — {report['overall']}")
    return report


# ---------------------------------------------------------------------------
# Step 3: Feature engineering
# ---------------------------------------------------------------------------


def engineer_features(df: pd.DataFrame) -> tuple[pd.DataFrame, FrequencyEncoder]:
    freq_enc = FrequencyEncoder(columns=["merchant_id", "device_type"], normalize=True)
    df_feat = freq_enc.fit_transform(df.copy())

    df_feat["balance_delta"] = df_feat["new_balance"] - (
        df_feat["old_balance"] - df_feat["transaction_amount"]
    )
    df_feat["balance_error"] = df_feat["balance_delta"].abs()
    df_feat["balance_zeroed"] = (df_feat["new_balance"] == 0).astype(int)

    return df_feat, freq_enc


# ---------------------------------------------------------------------------
# Step 4 & 5: Training + evaluation
# ---------------------------------------------------------------------------

FEATURE_COLS = [
    "transaction_amount",
    "hour_of_day",
    "day_of_week",
    "merchant_id",
    "device_type",
    "is_international",
    "old_balance",
    "new_balance",
    "balance_delta",
    "balance_error",
    "balance_zeroed",
]


def train_and_evaluate(df: pd.DataFrame, seed: int = 42) -> dict:
    x = df[FEATURE_COLS]
    y = df["is_fraud"]

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=seed,
        stratify=y,
    )

    results = {}

    # Model 1: LightGBM
    lgbm = lgb.LGBMClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        num_leaves=31,
        random_state=seed,
        verbose=-1,
    )
    lgbm.fit(x_train, y_train)
    y_prob_lgbm = lgbm.predict_proba(x_test)[:, 1]
    eval_lgbm = ClassificationEvaluator(y_test, y_prob_lgbm, model_name="LightGBM")
    results["LightGBM"] = {"model": lgbm, "metrics": eval_lgbm.summary()}

    # Model 2: Logistic Regression
    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)
    lr = LogisticRegression(max_iter=1000, random_state=seed)
    lr.fit(x_train_scaled, y_train)
    y_prob_lr = lr.predict_proba(x_test_scaled)[:, 1]
    eval_lr = ClassificationEvaluator(y_test, y_prob_lr, model_name="LogisticRegression")
    results["LogisticRegression"] = {"model": lr, "metrics": eval_lr.summary(), "scaler": scaler}

    return results


# ---------------------------------------------------------------------------
# Step 6: Champion selection + registration
# ---------------------------------------------------------------------------


def select_champion(results: dict, prod_metrics: dict = None) -> str:
    challenger_name = max(results, key=lambda k: results[k]["metrics"]["ROC-AUC"])
    challenger_auc = results[challenger_name]["metrics"]["ROC-AUC"]

    if prod_metrics and "ROC-AUC" in prod_metrics:
        prod_auc = prod_metrics["ROC-AUC"]
        print(f"\n  Challenger: {challenger_name} (AUC={challenger_auc:.4f})")
        print(f"  Production: {prod_auc:.4f}")

        if challenger_auc > prod_auc:
            print(f"  [*] SUCCESS: Challenger outperformed Production. Selecting {challenger_name}.")
            return challenger_name
        else:
            print("  [!] REJECTED: Challenger did not outperform Production. Keeping current system.")
            return None

    print(f"\n  Champion (Initial): {challenger_name} (AUC={challenger_auc:.4f})")
    return challenger_name


def register_model(model, model_name: str, metrics: dict, data_hash: str, params: dict):
    # Find next version
    if REGISTRY_DIR.exists():
        existing = [
            int(d.name.lstrip("v"))
            for d in REGISTRY_DIR.iterdir()
            if d.is_dir() and d.name.startswith("v")
        ]
        version = max(existing, default=0) + 1
    else:
        version = 1

    version_dir = REGISTRY_DIR / f"v{version}"
    version_dir.mkdir(parents=True, exist_ok=True)

    # Save model
    joblib.dump(model, version_dir / "model.joblib")

    # Save metadata
    metadata = {
        "version": version,
        "model_name": model_name,
        "stage": "staging",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data_hash": data_hash,
        "metrics": {k: round(v, 6) for k, v in metrics.items()},
        "params": params,
    }
    with open(version_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"  Registered {model_name} as v{version} (stage=staging)")
    return metadata


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_pipeline():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    # Registry is now persistent to support Champion-Challenger logic

    t0 = time.time()

    # Step 1
    print("=== Step 1/6: Data Generation ===")
    df = generate_data()
    data_hash = hashlib.sha256(pd.util.hash_pandas_object(df).values.tobytes()).hexdigest()[:16]
    print(f"  Generated {len(df)} rows (hash={data_hash})")

    # Step 2
    print("\n=== Step 2/6: Data Validation ===")
    validation = validate_data(df)
    with open(RESULTS_DIR / "validation_report.json", "w") as f:
        json.dump(validation, f, indent=2)
    if validation["overall"] == "FAIL":
        print("  PIPELINE BLOCKED: Data validation failed")
        return

    # Step 3
    print("\n=== Step 3/6: Feature Engineering ===")
    df_feat, freq_enc = engineer_features(df)
    print(f"  {len(FEATURE_COLS)} features engineered")

    # Step 4+5
    print("\n=== Step 4/6: Training + Step 5/6: Evaluation ===")
    results = train_and_evaluate(df_feat)

    # Step 6
    print("\n=== Step 6/6: Champion Selection + Registration ===")

    # Load current production metrics if any
    prod_metrics = None
    last_version = 0
    if REGISTRY_DIR.exists():
        versions = sorted([int(d.name.lstrip("v")) for d in REGISTRY_DIR.iterdir() if d.name.startswith("v")])
        if versions:
            last_version = versions[-1]
            with open(REGISTRY_DIR / f"v{last_version}" / "metadata.json") as f:
                prod_metrics = json.load(f).get("metrics")

    champion_name = select_champion(results, prod_metrics)

    if champion_name:
        champion = results[champion_name]
        params = (
            {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.05}
            if champion_name == "LightGBM"
            else {"max_iter": 1000}
        )
        metadata = register_model(
            champion["model"], champion_name, champion["metrics"], data_hash, params
        )
        registered_version = metadata["version"]
        champion_metrics = {k: round(v, 6) for k, v in champion["metrics"].items()}
    else:
        print("  Pipeline finished without registration (challenger underperformed)")
        registered_version = last_version
        champion_name = "Production (Unchanged)"
        champion_metrics = prod_metrics

    # Write consolidated metrics
    duration = time.time() - t0
    metrics_output = {
        "pipeline_duration_sec": round(duration, 2),
        "data_hash": data_hash,
        "data_rows": len(df),
        "models_evaluated": {
            name: {k: round(v, 6) for k, v in r["metrics"].items()} for name, r in results.items()
        },
        "champion": champion_name,
        "champion_metrics": champion_metrics,
        "registered_version": registered_version,
    }
    with open(RESULTS_DIR / "metrics.json", "w") as f:
        json.dump(metrics_output, f, indent=2)

    print(f"\n=== Pipeline complete in {duration:.1f}s ===")
    print(f"  Results:  {RESULTS_DIR / 'metrics.json'}")
    if champion_name != "Production (Unchanged)":
        version_tag = f"v{metadata['version']}"
        print(f"  Model:    {REGISTRY_DIR / version_tag}")
    else:
        print(f"  Model:    {REGISTRY_DIR / f'v{registered_version}'} (using current production)")
    return metrics_output


if __name__ == "__main__":
    run_pipeline()
