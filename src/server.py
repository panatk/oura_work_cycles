"""Flask web server for Oura Smart Calendar."""

import logging
import json
from datetime import datetime
from typing import Optional

from flask import Flask, Response, jsonify
import pytz

from config import DEBUG, PORT, TIMEZONE, OURA_TOKEN, OURA_CLIENT_ID
from src.oura_client import OuraClient
from src.analyzer import OuraAnalyzer
from src.calendar_gen import CalendarGenerator

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Global instances (initialized on startup)
oura_client: Optional[OuraClient] = None
analyzer: Optional[OuraAnalyzer] = None
calendar_gen: Optional[CalendarGenerator] = None
current_schedule = None
current_patterns = None


def initialize():
    """Initialize API clients and analyzers."""
    global oura_client, analyzer, calendar_gen

    try:
        # Check if we have auth credentials
        if not OURA_TOKEN and not OURA_CLIENT_ID:
            raise ValueError(
                "No Oura credentials found. Set OURA_TOKEN or OURA_CLIENT_ID/SECRET env vars."
            )

        oura_client = OuraClient(access_token=OURA_TOKEN)
        analyzer = OuraAnalyzer()
        calendar_gen = CalendarGenerator()

        logger.info("Successfully initialized Oura client and analyzer")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        return False


def refresh_data():
    """Fetch fresh data and regenerate schedule."""
    global current_schedule, current_patterns

    try:
        if not oura_client or not analyzer:
            logger.warning("Clients not initialized")
            return False

        logger.info("Refreshing Oura data...")

        # Fetch all data
        all_data = oura_client.get_all_data()

        # Analyze patterns
        current_patterns = analyzer.analyze_historical_data(all_data)

        # Get today's readiness score
        readiness_data = all_data.get("readiness", [])
        today_readiness = 70  # Default fallback

        if readiness_data:
            # Find today's readiness
            today_str = datetime.now().date().isoformat()
            for record in readiness_data:
                if record.get("day") == today_str:
                    today_readiness = record.get("score", 70)
                    break

        # Generate today's schedule
        tz = pytz.timezone(TIMEZONE)
        today = datetime.now(tz)

        # Try to get wake time from last night's sleep
        wake_time = None
        sleep_periods = all_data.get("sleep_periods", [])
        if sleep_periods:
            last_sleep = sleep_periods[-1]
            wake_time_str = last_sleep.get("bedtime_end")
            if wake_time_str:
                try:
                    wake_dt = datetime.fromisoformat(wake_time_str.replace("Z", "+00:00"))
                    wake_time = wake_dt.astimezone(tz)
                except Exception as e:
                    logger.debug(f"Could not parse wake time: {e}")

        current_schedule = analyzer.generate_daily_schedule(
            readiness_score=today_readiness, wake_time=wake_time, today_date=today
        )

        logger.info(f"Data refresh complete. Today's readiness: {today_readiness}")
        return True
    except Exception as e:
        logger.error(f"Failed to refresh data: {e}")
        return False


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


@app.route("/status", methods=["GET"])
def status():
    """Return current status and schedule."""
    if not current_schedule:
        return jsonify({"error": "No schedule generated yet. Call /analyze first."}), 400

    tz = pytz.timezone(TIMEZONE)
    schedule_info = []
    for block in current_schedule:
        schedule_info.append(
            {
                "title": block["title"],
                "type": block["type"],
                "start": block["start"].isoformat(),
                "end": block["end"].isoformat(),
                "description": block["description"],
            }
        )

    return jsonify(
        {
            "timestamp": datetime.now(tz).isoformat(),
            "patterns": current_patterns,
            "schedule": schedule_info,
        }
    )


@app.route("/calendar.ics", methods=["GET"])
def calendar_ics():
    """Return the ICS calendar feed."""
    if not current_schedule:
        return (
            Response(
                "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Oura//Empty//EN\nEND:VCALENDAR",
                mimetype="text/calendar",
            ),
            400,
        )

    ics_content = calendar_gen.generate_ics(current_schedule)

    # Set cache headers - refresh every 6 hours
    response = Response(ics_content, mimetype="text/calendar")
    response.headers["Cache-Control"] = "public, max-age=21600"
    response.headers["Content-Disposition"] = "attachment; filename=oura-calendar.ics"

    return response


@app.route("/analyze", methods=["GET", "POST"])
def analyze():
    """Manually trigger data refresh and analysis."""
    success = refresh_data()

    if success:
        return jsonify(
            {
                "status": "success",
                "message": "Data refreshed and schedule regenerated",
                "timestamp": datetime.now().isoformat(),
            }
        )
    else:
        return (
            jsonify({"status": "error", "message": "Failed to refresh data"}),
            500,
        )


@app.route("/", methods=["GET"])
def index():
    """Root endpoint with API documentation."""
    return jsonify(
        {
            "service": "Oura Smart Calendar",
            "endpoints": {
                "GET /calendar.ics": "Subscribe to this ICS feed in Google Calendar",
                "GET /health": "Health check",
                "GET /status": "Current status and today's schedule",
                "GET /analyze": "Force refresh of Oura data and schedule",
            },
            "setup": {
                "step1": "Get Oura Personal Access Token from https://cloud.ouraring.com",
                "step2": "Set OURA_TOKEN env var",
                "step3": "Subscribe to /calendar.ics in Google Calendar",
            },
        }
    )


def main():
    """Main entry point."""
    logger.info(f"Starting Oura Smart Calendar (timezone: {TIMEZONE})")

    if not initialize():
        logger.error("Failed to initialize. Exiting.")
        return

    if not refresh_data():
        logger.warning("Initial data refresh failed. Server may have limited functionality.")

    logger.info(f"Starting Flask server on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)


if __name__ == "__main__":
    main()
