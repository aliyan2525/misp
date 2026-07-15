import pandas as pd
import numpy as np
from datetime import date, timedelta

# Lock random seed for reproducibility
np.random.seed(42)

channels = ['Google Ads', 'Meta Ads', 'SEO', 'Email']
campaigns = [f"{ch} - Campaign {i}" for ch in channels for i in range(1, 3)]
rows = []
start = date(2026, 1, 1)

for day_offset in range(90):
    current_date = start + timedelta(days=day_offset)
    for camp in campaigns:
        clicks = int(np.random.poisson(50))
        
        if "SEO" in camp:
            cost = 0.0
        else:
            cost = float(round(clicks * np.random.uniform(0.5, 3.0), 2))
            
        rows.append({
            'campaign_name': camp,
            'metric_date': current_date, 
            'clicks': clicks,
            'impressions': int(clicks * np.random.randint(8, 15)),
            'cost': cost,
            'conversions': int(np.random.binomial(clicks, 0.03))
        })

df = pd.DataFrame(rows)
df.to_csv('generated_daily_metrics.csv', index=False)
print("Successfully generated generated_daily_metrics.csv with 720 rows.")