import os
import pandas as pd
from sqlalchemy import create_engine

# Database credentials
db_user = "postgres"
db_password = "postgree"  # <-- PUT YOUR ACTUAL PGADMIN PASSWORD HERE
db_host = "localhost"
db_port = "5432"
db_name = "misp_db"

# Build connection url
DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
engine = create_engine(DATABASE_URL)

try:
    # Read the generated CSV file
    df = pd.read_csv('generated_daily_metrics.csv')

    # Query your freshly seeded campaigns to map names to official IDs
    campaigns_lookup = pd.read_sql('SELECT campaign_id, name FROM campaigns', engine)

    # Merge dataset to swap campaign text names for structural foreign keys
    df = df.merge(campaigns_lookup, left_on='campaign_name', right_on='name')

    # Filter and reorder columns to match the daily_metrics target schema columns exactly
    final_df = df[['campaign_id', 'metric_date', 'clicks', 'impressions', 'cost', 'conversions']]

    # Append records directly into your database
    final_df.to_sql('daily_metrics', engine, if_exists='append', index=False)
    print(f"Pipeline complete: Loaded {len(final_df)} daily timeline rows into 'daily_metrics'!")

except Exception as e:
    print(f"Pipeline failed: {e}")