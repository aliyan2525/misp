import pandas as pd
from recommendations import generate_recommendations


def test_zero_conversion_campaign_triggers_high_priority_pause_rule():
    campaign_df = pd.DataFrame([
        {"name": "Dead Campaign", "total_cost": 200.0, "total_conversions": 0},
        {"name": "Healthy Campaign", "total_cost": 100.0, "total_conversions": 20},
    ])
    recs = generate_recommendations(campaign_df, forecast_df=None)

    dead_campaign_recs = [r for r in recs if r["campaign"] == "Dead Campaign"]
    assert len(dead_campaign_recs) >= 1
    assert dead_campaign_recs[0]["priority"] == "high"


def test_empty_campaign_data_returns_no_recommendations():
    empty_df = pd.DataFrame(columns=["name", "total_cost", "total_conversions"])
    recs = generate_recommendations(empty_df, forecast_df=None)
    assert recs == []


def test_efficient_campaign_gets_increase_budget_recommendation():
    campaign_df = pd.DataFrame([
        {"name": "Cheap Winner", "total_cost": 10.0, "total_conversions": 50},
        {"name": "Expensive Loser", "total_cost": 500.0, "total_conversions": 5},
    ])
    recs = generate_recommendations(campaign_df, forecast_df=None)

    winner_recs = [r for r in recs if r["campaign"] == "Cheap Winner"]
    assert len(winner_recs) >= 1
    assert "increasing its budget" in winner_recs[0]["recommendation"]


def test_declining_forecast_trend_triggers_warning():
    campaign_df = pd.DataFrame([
        {"name": "Any Campaign", "total_cost": 100.0, "total_conversions": 10},
    ])
    # 14 days of steadily declining predicted conversions
    forecast_df = pd.DataFrame({
        "predicted_conversions": [30 - i for i in range(14)]
    })
    recs = generate_recommendations(campaign_df, forecast_df)

    trend_recs = [r for r in recs if r["campaign"] == "All channels"]
    assert len(trend_recs) == 1
    assert "declining" in trend_recs[0]["recommendation"]
