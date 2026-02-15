import sqlite3

from realtime_ml_system.demo.online_inference import MetricsLogger

def test_sqlite_logging_and_percentiles(tmp_path):
    """Test that inference metrics are logged to SQLite and percentiles are correct."""
    db_file = tmp_path / "test_metrics.db"
    logger = MetricsLogger(db_file)

    # Log some dummy latencies: 10, 20, 30, 40, 50
    for lat in [10, 20, 30, 40, 50]:
        logger.log_inference(lat, 0.5, 0)

    stats = logger.get_percentiles()

    # P50 of [10, 20, 30, 40, 50] is 30
    assert stats["p50"] == 30.0
    # P99 should be close to 50
    assert stats["p99"] >= 40.0

    # Verify DB actually exists and has rows
    conn = sqlite3.connect(db_file)
    count = conn.execute("SELECT COUNT(*) FROM inference_logs").fetchone()[0]
    assert count == 5
    conn.close()
