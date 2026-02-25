#!/usr/bin/env python3
"""Convert Oura CSV export to mock JSON data for testing."""

import csv
import json
from datetime import datetime, timedelta

csv_file = "/Users/karanpanat/Downloads/oura_2024-10-01_2026-02-25_trends.csv"
output_file = "/Users/karanpanat/Source/oura_work_cycles/mock_oura_data.json"

readiness_data = []
sleep_data = []

with open(csv_file, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        date_str = row['date'].strip()
        score_str = row['Readiness Score'].strip()

        if not date_str or not score_str:
            continue

        try:
            score = int(score_str)

            # Add readiness record
            readiness_data.append({
                "day": date_str,
                "score": score
            })

            # Generate realistic sleep periods in UTC
            # Assuming: bedtime at 11 PM Sydney time, wake at 7 AM Sydney time next day
            # Sydney UTC+11: 11 PM Sydney = 12 PM UTC (previous day), 7 AM Sydney = 8 PM UTC (previous day)
            date_obj = datetime.fromisoformat(date_str)

            # For readiness on date X, assume sleep from 11 PM on night of X to 7 AM on X+1
            # bedtime_start: 11 PM on date X in Sydney = 12 PM UTC on date X
            bed_time_utc = date_obj.replace(hour=12, minute=0, second=0)  # UTC time (11 PM Sydney = 12 PM UTC)

            # bedtime_end: 7 AM on date X+1 in Sydney = 8 PM UTC on date X
            wake_time_utc = (date_obj + timedelta(days=1)).replace(hour=20, minute=0, second=0)  # UTC time (7 AM Sydney next day = 8 PM UTC same day)

            sleep_data.append({
                "bedtime_start": bed_time_utc.isoformat() + "Z",
                "bedtime_end": wake_time_utc.isoformat() + "Z"
            })
        except (ValueError, KeyError):
            continue

# Create mock data structure
mock_data = {
    "readiness": readiness_data,
    "sleep": [],
    "activity": [],
    "sleep_periods": sleep_data
}

with open(output_file, 'w') as f:
    json.dump(mock_data, f, indent=2)

print(f"✅ Created mock data with {len(readiness_data)} readiness records")
print(f"✅ Created {len(sleep_data)} sleep periods")
print(f"✅ Saved to: {output_file}")
