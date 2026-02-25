#!/usr/bin/env python3
"""Test Oura API connection and data fetching."""

import sys
import logging
import os
from datetime import datetime
from dotenv import load_dotenv

# Load .env file
load_dotenv('/Users/karanpanat/Source/oura_work_cycles/.env')

# Add src to path
sys.path.insert(0, '/Users/karanpanat/Source/oura_work_cycles')

from src.oura_client import OuraClient
from src.analyzer import OuraAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        logger.info("🔗 Testing Oura API connection...")

        # Initialize client
        client = OuraClient()
        logger.info("✅ Oura client initialized successfully")

        # Fetch data
        logger.info("📊 Fetching last 7 days of data...")
        all_data = client.get_all_data(
            start_date=(datetime.now().date() - __import__('datetime').timedelta(days=7)).isoformat(),
            end_date=datetime.now().date().isoformat()
        )

        # Check what we got
        readiness = all_data.get('readiness', [])
        sleep = all_data.get('sleep', [])
        activity = all_data.get('activity', [])
        sleep_periods = all_data.get('sleep_periods', [])

        logger.info(f"✅ Readiness records: {len(readiness)}")
        logger.info(f"✅ Sleep records: {len(sleep)}")
        logger.info(f"✅ Activity records: {len(activity)}")
        logger.info(f"✅ Sleep periods: {len(sleep_periods)}")

        if readiness:
            latest = readiness[-1]
            logger.info(f"\n📈 Latest readiness score: {latest.get('score', 'N/A')} on {latest.get('day', 'N/A')}")

        if sleep_periods:
            latest_sleep = sleep_periods[-1]
            logger.info(f"😴 Latest sleep: {latest_sleep.get('total_sleep_duration', 'N/A')}s (efficiency: {latest_sleep.get('sleep_efficiency', 'N/A')}%)")

        # Test analyzer
        logger.info("\n🧠 Testing pattern analysis...")
        analyzer = OuraAnalyzer()
        patterns = analyzer.analyze_historical_data(all_data)
        logger.info(f"✅ Chronotype detected: {patterns.get('chronotype')}")
        logger.info(f"✅ Average wake time: {patterns.get('average_wake_time')}")

        # Test schedule generation
        logger.info("\n📅 Generating today's schedule...")
        schedule = analyzer.generate_daily_schedule(readiness_score=80)
        logger.info(f"✅ Generated {len(schedule)} time blocks")
        for block in schedule[:3]:
            logger.info(f"   - {block['title']}: {block['start'].strftime('%H:%M')} - {block['end'].strftime('%H:%M')}")

        logger.info("\n🎉 All tests passed! Your Oura connection is working.")
        return 0

    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())
