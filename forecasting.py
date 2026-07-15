import pandas as pd
from prophet import Prophet
from sqlalchemy import text

from database import engine


def generate_conversion_forecast(org_id: int, days_to_predict: int = 30):
    """
    Builds a 30-day conversion forecast scoped to a single organization.
    org_id is required so one tenant's forecast never includes another
    tenant's data.
    """
    query = text("""
        SELECT m.metric_date as ds, SUM(m.conversions) as y
        FROM daily_metrics m
        JOIN campaigns c ON m.campaign_id = c.campaign_id
        WHERE c.org_id = :org_id
        GROUP BY m.metric_date
        ORDER BY m.metric_date
    """)

    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"org_id": org_id})

    if df.empty or len(df) < 2:
        return []

    df['ds'] = pd.to_datetime(df['ds'])
    df['y'] = df['y'].astype(float)

    model = Prophet(yearly_seasonality=True, daily_seasonality=False)
    model.fit(df)

    future = model.make_future_dataframe(periods=days_to_predict)
    forecast = model.predict(future)

    forecast_clean = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(days_to_predict).copy()
    forecast_clean['ds'] = forecast_clean['ds'].dt.strftime('%Y-%m-%d')
    forecast_clean.columns = ['date', 'predicted_conversions', 'lower_bound', 'upper_bound']

    return forecast_clean.to_dict(orient="records")
