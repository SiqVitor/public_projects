import pytest
from unittest.mock import MagicMock, patch
from genai_agent.src.engine import ArgusEngine

@patch("google.generativeai.configure")
@patch("google.generativeai.GenerativeModel")
def test_engine_initialization(mock_model, mock_conf):
    """Test that the engine initializes correctly with an API key."""
    with patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"}):
        engine = ArgusEngine()
        assert engine is not None
        mock_conf.assert_called_once_with(api_key="test_key")

@patch("google.generativeai.GenerativeModel")
def test_intent_classification(mock_model):
    """Test that intent classification routes correctly."""
    with patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"}):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = "FINANCIAL_ANALYSIS"
        mock_model.return_value.generate_content.return_value = mock_response

        engine = ArgusEngine()
        intent = engine.classify_intent("What was the revenue in Q3?")
        assert intent == "FINANCIAL_ANALYSIS"

def test_tools_logic():
    """Test that grounding tools return expected outputs."""
    from genai_agent.src.tools import calculate_metric, lookup_operational_presence

    # Test calculation
    res = calculate_metric("math.sqrt(16)")
    assert "4.0" in res

    # Test lookup
    res = lookup_operational_presence("Brazil")
    assert "Primary hub" in res
