#!/usr/bin/env python3
"""Convert Oura CSV export to mock JSON data for testing."""

import csv
import json
from datetime import datetime

# Use the detailed sleep data CSV with real timestamps
csv_file = "/Users/karanpanat/Downloads/oura_2024-10-01_2026-02-25_trends (1).csv"
output_file = "/Users/karanpanat/Source/oura_work_cycles/mock_oura_data.json"

readiness_data = []
sleep_data = []

with open(csv_file, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        date_str = row['date'].strip()
        readiness_str = row['Readiness Score'].strip()
        bedtime_start_str = row['Bedtime Start'].strip()
        bedtime_end_str = row['Bedtime End'].strip()

        if not date_str or not readiness_str:
            continue

        try:
            readiness = int(readiness_str)

            # Add readiness record
            readiness_data.append({
                "day": date_str,
                "score": readiness
            })

            # Use actual bedtime/wake times from Oura data
            if bedtime_start_str and bedtime_end_str:
                # Parse the ISO format timestamps with timezone (Oura format includes +10:00, +11:00, etc)
                bed_time = datetime.fromisoformat(bedtime_start_str)
                wake_time = datetime.fromisoformat(bedtime_end_str)

                sleep_data.append({
                    "bedtime_start": bed_time.isoformat(),
                    "bedtime_end": wake_time.isoformat()
                })
        except (ValueError, KeyError) as e:
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
print(f"✅ Created {len(sleep_data)} sleep periods (using REAL Oura sleep data)")
print(f"✅ Saved to: {output_file}")
