import numpy as np

from ml_platform.demo.pipeline import calculate_psi, select_champion

def test_psi_calculation():
    """Test that PSI identifies drift between distributions."""
    expected = np.random.normal(10, 1, 1000)
    actual_drift = np.random.normal(15, 1, 1000) # Increased mean to ensure high PSI

    psi_low = calculate_psi(expected, expected + np.random.normal(0, 0.1, 1000))
    psi_high = calculate_psi(expected, actual_drift)

    assert psi_low < 0.1
    assert psi_high > 0.2

def test_champion_challenger_logic():
    """Test that a better model is selected as champion."""
    results = {
        "NewModel": {"metrics": {"ROC-AUC": 0.95}}
    }
    prod_metrics_low = {"ROC-AUC": 0.90}
    prod_metrics_high = {"ROC-AUC": 0.97}

    # Case 1: Challenger wins
    winner = select_champion(results, prod_metrics_low)
    assert winner == "NewModel"

    # Case 2: Challenger loses
    winner = select_champion(results, prod_metrics_high)
    assert winner is None
