"""Flask web server for Oura Smart Calendar."""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import urlencode
from pathlib import Path

from flask import Flask, Response, jsonify, redirect, request, send_file
import pytz

from config import (
    DEBUG,
    PORT,
    TIMEZONE,
    OURA_TOKEN,
    OURA_CLIENT_ID,
    OURA_CLIENT_SECRET,
    OURA_REDIRECT_URI,
    OURA_API_BASE,
)
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
mock_data: Optional[Dict[str, Any]] = None
using_mock_data = False


def initialize():
    """Initialize API clients and analyzers."""
    global oura_client, analyzer, calendar_gen, mock_data, using_mock_data

    try:
        # Check for mock data first
        mock_data_file = Path("mock_oura_data.json")
        if mock_data_file.exists():
            try:
                with open(mock_data_file, 'r') as f:
                    mock_data = json.load(f)
                    logger.info(f"✅ Loaded mock data from {mock_data_file}")
                    logger.info(f"   - {len(mock_data.get('readiness', []))} readiness records")
                    logger.info(f"   - {len(mock_data.get('sleep_periods', []))} sleep periods")
                    using_mock_data = True
                    oura_client = None
            except Exception as e:
                logger.error(f"Failed to load mock data: {e}")
                return False
        else:
            # Check if we have auth credentials for real API
            if not OURA_TOKEN and not OURA_CLIENT_ID:
                raise ValueError(
                    "No Oura credentials found and no mock data available. "
                    "Set OURA_TOKEN or OURA_CLIENT_ID/SECRET env vars, or place mock_oura_data.json in the app directory."
                )

            # Try to initialize Oura client
            # If no direct token, it will check for cached token or return None
            try:
                oura_client = OuraClient(access_token=OURA_TOKEN)
                logger.info("Successfully initialized Oura client")
                using_mock_data = False
            except ValueError as e:
                logger.warning(f"Oura client initialization: {e}")
                logger.info("User must authorize via /authorize endpoint")
                oura_client = None

        analyzer = OuraAnalyzer()
        calendar_gen = CalendarGenerator()

        logger.info("Successfully initialized analyzer and calendar generator")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        return False


def refresh_data():
    """Fetch fresh data and regenerate schedule."""
    global current_schedule, current_patterns

    try:
        if not analyzer:
            logger.warning("Analyzer not initialized")
            return False

        logger.info("Refreshing Oura data...")

        # Fetch all data (use mock data if available, otherwise call API)
        if using_mock_data and mock_data:
            logger.info("Using mock data for analysis")
            all_data = mock_data
        elif oura_client:
            all_data = oura_client.get_all_data()
        else:
            logger.error("No data source available (no mock data and no API client)")
            return False

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

        # Use average wake time from patterns (more representative than last night's sleep)
        wake_time = None
        if current_patterns.get("average_wake_time"):
            try:
                avg_wake_str = current_patterns["average_wake_time"]
                parts = avg_wake_str.split(":")
                wake_hour = int(parts[0])
                wake_min = int(parts[1])
                wake_time = today.replace(hour=wake_hour, minute=wake_min, second=0, microsecond=0)
            except Exception as e:
                logger.debug(f"Could not parse average wake time: {e}")

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
            "data_source": "mock" if using_mock_data else "oura_api",
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


@app.route("/authorize", methods=["GET"])
def authorize():
    """Redirect user to Oura for OAuth2 authorization."""
    if not OURA_CLIENT_ID:
        return jsonify({"error": "OURA_CLIENT_ID not configured"}), 400

    params = {
        "client_id": OURA_CLIENT_ID,
        "redirect_uri": OURA_REDIRECT_URI,
        "response_type": "code",
        "scope": "email heartrate session stress personal heart_health tag spo2 daily workout ring_configuration",
    }

    auth_url = f"{OURA_API_BASE}/oauth/authorize?{urlencode(params)}"
    logger.info(f"Redirecting to Oura authorization: {auth_url}")
    return redirect(auth_url)


@app.route("/callback", methods=["GET"])
def callback():
    """Handle OAuth2 callback from Oura."""
    code = request.args.get("code")
    error = request.args.get("error")

    if error:
        logger.error(f"OAuth error: {error}")
        return jsonify({"error": f"Authorization failed: {error}"}), 400

    if not code:
        return jsonify({"error": "No authorization code received"}), 400

    logger.info("Received authorization code from Oura. Exchanging for token...")

    # Exchange code for token
    token = OuraClient.exchange_auth_code(code)

    if token:
        logger.info("✅ Successfully obtained access token!")
        refresh_data()  # Refresh data with new token
        return jsonify(
            {
                "status": "success",
                "message": "Authorization successful! You can now subscribe to /calendar.ics in Google Calendar.",
            }
        )
    else:
        logger.error("Failed to exchange authorization code for token")
        return jsonify({"error": "Failed to obtain access token"}), 400


@app.route("/dashboard", methods=["GET"])
def dashboard():
    """Serve the interactive dashboard."""
    dashboard_file = Path(__file__).parent / "dashboard.html"
    if dashboard_file.exists():
        with open(dashboard_file, 'r') as f:
            html_content = f.read()
        return Response(html_content, mimetype="text/html")
    else:
        return jsonify({"error": "Dashboard not found"}), 404


@app.route("/", methods=["GET"])
def index():
    """Root endpoint with API documentation."""
    mode_info = "🔄 Using mock data (local testing)" if using_mock_data else "🔐 Using Oura API (OAuth2)"

    if using_mock_data:
        setup_steps = {
            "step1": "Visit /dashboard to view your dashboard",
            "step2": "Visit /status to see raw schedule data",
            "step3": "Visit /calendar.ics to get the ICS feed for Google Calendar",
        }
    else:
        setup_steps = {
            "step1": "Visit /authorize to authorize with Oura",
            "step2": "Subscribe to /calendar.ics in Google Calendar",
            "step3": "Enjoy your personalized schedule!",
        }

    return jsonify(
        {
            "service": "Oura Smart Calendar",
            "mode": mode_info,
            "endpoints": {
                "GET /dashboard": "📊 Interactive visual dashboard",
                "GET /authorize": "Start OAuth2 authorization with Oura (if using API)",
                "GET /callback": "OAuth2 callback endpoint (handled automatically)",
                "GET /calendar.ics": "Subscribe to this ICS feed in Google Calendar",
                "GET /health": "Health check",
                "GET /status": "Current status and today's schedule (JSON)",
                "GET /analyze": "Force refresh of Oura data and schedule",
            },
            "setup": setup_steps,
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
