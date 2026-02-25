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

            # Generate approximate sleep periods (assuming 11 PM bedtime, 7 AM wake)
            # This is estimated since we don't have exact times
            bed_time = datetime.fromisoformat(date_str) - timedelta(hours=1)
            wake_time = datetime.fromisoformat(date_str) + timedelta(hours=7)

            sleep_data.append({
                "bedtime_start": bed_time.isoformat() + "Z",
                "bedtime_end": wake_time.isoformat() + "Z"
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
