import json
import sys
import time
import sqlite3
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

# Ensure ds_tools and local modules are importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ds_tools" / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from stream_simulator import generate_feature_store, stream_events

RESULTS_DIR = Path(__file__).parent / "results"
DB_PATH = RESULTS_DIR / "metrics.db"

FEATURE_COLS = [
    "transaction_amount",
    "hour_of_day",
    "is_international",
    "avg_daily_spend_30d",
    "txn_count_7d",
    "distinct_merchants_30d",
    "merchant_freq",
    "velocity_1h",
]

class MetricsLogger:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS inference_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    latency_ms FLOAT,
                    prediction FLOAT,
                    is_fraud_label INTEGER
                )
            """)

    def log_inference(self, latency_ms: float, prediction: float, label: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO inference_logs (latency_ms, prediction, is_fraud_label) VALUES (?, ?, ?)",
                (latency_ms, prediction, label)
            )

    def get_percentiles(self):
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT latency_ms FROM inference_logs"
            latencies = [row[0] for row in conn.execute(query).fetchall()]
        if not latencies:
            return {}
        return {
            "p50": np.percentile(latencies, 50),
            "p95": np.percentile(latencies, 95),
            "p99": np.percentile(latencies, 99)
        }

class ScoringApp:
    """Simulates a FastAPI web service for online inference."""
    def __init__(self, model: lgb.LGBMClassifier, feature_store: dict, logger: MetricsLogger):
        self.model = model
        self.feature_store = feature_store
        self.logger = logger

    def post_score(self, event: dict) -> dict:
        """Simulated POST /score endpoint."""
        t0 = time.perf_counter()

        # 1. Feature Assembly
        store_feats = self.feature_store.get(event["entity_id"], {c: 0.0 for c in FEATURE_COLS if c not in event})
        row = {**event, **store_feats}
        features = pd.DataFrame([{c: row.get(c, 0.0) for c in FEATURE_COLS}])

        # 2. Prediction
        prob = float(self.model.predict_proba(features)[:, 1][0])

        # 3. Decision & Logging
        latency_ms = (time.perf_counter() - t0) * 1000
        self.logger.log_inference(latency_ms, prob, event.get("_label", -1))

        return {"prob": prob, "latency_ms": latency_ms}

def batch_train(seed: int = 42) -> lgb.LGBMClassifier:
    """Train a model on synthetic historical data (batch phase)."""
    rng = np.random.RandomState(seed)
    n = 2000 # Reduced for speed in demo
    labels = rng.binomial(1, 0.05, n)
    feature_store = generate_feature_store(seed=seed)

    rows = []
    for i in range(n):
        entity_id = rng.randint(0, 500)
        store_feats = feature_store.get(entity_id, {c: 0.0 for c in FEATURE_COLS})
        amount = rng.lognormal(6.5, 0.8) if labels[i] else rng.lognormal(4.5, 1.0)
        rows.append({"transaction_amount": round(amount, 2), "hour_of_day": int(rng.choice(24)), "is_international": int(rng.random() < 0.1), **store_feats})

    df = pd.DataFrame(rows)
    x_train, x_val, y_train, y_val = train_test_split(df[FEATURE_COLS], labels, test_size=0.2, random_state=seed)

    model = lgb.LGBMClassifier(n_estimators=50, verbose=-1)
    model.fit(x_train, y_train)
    return model

def run():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists(): DB_PATH.unlink()

    print("=== Production Real-Time System Demo ===")

    # 1. Batch Training
    model = batch_train()
    feature_store = generate_feature_store()
    logger = MetricsLogger(DB_PATH)
    app = ScoringApp(model, feature_store, logger)

    # 2. Online Inference
    print("[*] Simulating live credit card transaction stream...")
    n_events = 500
    for event in stream_events(n_events=n_events):
        app.post_score(event)
        if event["event_id"] % 100 == 0:
            print(f"  Processed {event['event_id']} events...")

    # 3. Analyze Results from SQLite
    stats = logger.get_percentiles()
    print("\n=== Performance Analysis (from SQLite) ===")
    print(f"  Latency P50: {stats['p50']:.4f} ms")
    print(f"  Latency P95: {stats['p95']:.4f} ms")
    print(f"  Latency P99: {stats['p99']:.4f} ms")

    summary = {
        "engine": "production_sim (sqlite_logged)",
        "events": n_events,
        "metrics": stats
    }
    with open(RESULTS_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nFinal report saved to {RESULTS_DIR}")

if __name__ == "__main__":
    run()
