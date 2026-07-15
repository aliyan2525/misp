import pandas as pd


def generate_recommendations(campaign_df: pd.DataFrame, forecast_df: pd.DataFrame) -> list:
    """
    Rule-based recommendation engine.
    campaign_df expects columns: name, total_cost, total_conversions
    forecast_df expects a 'predicted_conversions' column (from forecasting.py)
    """
    recommendations = []

    if campaign_df.empty:
        return recommendations

    campaign_df = campaign_df.copy()
    campaign_df["total_cost"] = campaign_df["total_cost"].astype(float)
    campaign_df["total_conversions"] = campaign_df["total_conversions"].astype(float)
    campaign_df["cost_per_conversion"] = campaign_df["total_cost"] / campaign_df["total_conversions"].replace(0, 1)
    avg_cpc = campaign_df["cost_per_conversion"].mean()

    for _, row in campaign_df.iterrows():
        if row["total_conversions"] == 0 and row["total_cost"] > 0:
            recommendations.append({
                "priority": "high",
                "campaign": row["name"],
                "recommendation": f"{row['name']} has spent money with zero conversions. Consider pausing it immediately and reviewing targeting."
            })
        elif row["cost_per_conversion"] > avg_cpc * 1.5:
            recommendations.append({
                "priority": "medium",
                "campaign": row["name"],
                "recommendation": f"{row['name']}'s cost per conversion is {round(row['cost_per_conversion'] / avg_cpc, 1)}x the account average. Consider reducing its budget."
            })

    top_performers = campaign_df.nsmallest(2, "cost_per_conversion")
    for _, row in top_performers.iterrows():
        recommendations.append({
            "priority": "medium",
            "campaign": row["name"],
            "recommendation": f"{row['name']} has a strong cost per conversion. Consider increasing its budget to capture more volume."
        })

    if forecast_df is not None and len(forecast_df) >= 14:
        recent_trend = forecast_df["predicted_conversions"].iloc[-14:].diff().mean()
        if recent_trend < 0:
            recommendations.append({
                "priority": "high",
                "campaign": "All channels",
                "recommendation": "The 30-day forecast shows a declining conversion trend. Review creative, targeting, and seasonality before the trend continues."
            })

    return recommendations