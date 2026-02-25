"""Configuration for Oura Smart Calendar."""

import os
from dotenv import load_dotenv

load_dotenv()

# Timezone
TIMEZONE = os.getenv("TIMEZONE", "Australia/Sydney")

# API Configuration
OURA_CLIENT_ID = os.getenv("OURA_CLIENT_ID")
OURA_CLIENT_SECRET = os.getenv("OURA_CLIENT_SECRET")
OURA_REDIRECT_URI = os.getenv("OURA_REDIRECT_URI", "http://localhost:8000/callback")
OURA_TOKEN = os.getenv("OURA_TOKEN")  # Legacy PAT if available

# App Settings
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
PORT = int(os.getenv("PORT", 8000))

# Oura API
OURA_API_BASE = "https://api.ouraring.com"
OURA_API_VERSION = "v2"
OURA_HISTORY_DAYS = 90

# Readiness thresholds
HIGH_ENERGY_THRESHOLD = 85
RECOVERY_THRESHOLD = 70

# Schedule templates (offsets relative to wake time)
SCHEDULE_TEMPLATES = {
    "high_energy": [
        {"offset_hours": 0.5, "duration_hours": 0.5, "type": "morning_routine", "title": "☀️ Morning Routine"},
        {"offset_hours": 1.0, "duration_hours": 2.5, "type": "deep_focus", "title": "🧠 Deep Focus — Peak Energy"},
        {"offset_hours": 3.5, "duration_hours": 0.5, "type": "break", "title": "☕ Break"},
        {"offset_hours": 4.0, "duration_hours": 2.0, "type": "deep_focus", "title": "🧠 Deep Focus — Extended"},
        {"offset_hours": 6.0, "duration_hours": 1.0, "type": "lunch", "title": "🍽️ Lunch"},
        {"offset_hours": 7.0, "duration_hours": 2.0, "type": "creative", "title": "🎨 Creative / Collaborative Work"},
        {"offset_hours": 9.0, "duration_hours": 1.5, "type": "admin", "title": "📋 Admin / Email / Meetings"},
        {"offset_hours": 10.5, "duration_hours": 1.0, "type": "exercise", "title": "🏃 Exercise"},
        {"offset_hours": 12.0, "duration_hours": 1.5, "type": "wind_down", "title": "🌙 Wind Down — No Screens"},
    ],
    "normal": [
        {"offset_hours": 0.5, "duration_hours": 0.5, "type": "morning_routine", "title": "☀️ Morning Routine"},
        {"offset_hours": 1.0, "duration_hours": 2.0, "type": "deep_focus", "title": "🧠 Deep Focus"},
        {"offset_hours": 3.0, "duration_hours": 0.5, "type": "break", "title": "☕ Break"},
        {"offset_hours": 3.5, "duration_hours": 1.5, "type": "deep_focus", "title": "🧠 Deep Focus"},
        {"offset_hours": 5.0, "duration_hours": 1.0, "type": "lunch", "title": "🍽️ Lunch"},
        {"offset_hours": 6.0, "duration_hours": 1.5, "type": "creative", "title": "🎨 Creative / Collaborative Work"},
        {"offset_hours": 7.5, "duration_hours": 2.0, "type": "admin", "title": "📋 Admin / Email / Meetings"},
        {"offset_hours": 9.5, "duration_hours": 1.0, "type": "exercise", "title": "🏃 Exercise"},
        {"offset_hours": 11.0, "duration_hours": 1.5, "type": "wind_down", "title": "🌙 Wind Down"},
    ],
    "recovery": [
        {"offset_hours": 0.5, "duration_hours": 1.0, "type": "morning_routine", "title": "☀️ Slow Morning — Recovery Day"},
        {"offset_hours": 1.5, "duration_hours": 1.5, "type": "deep_focus", "title": "🧠 Light Focus — Don't Push It"},
        {"offset_hours": 3.0, "duration_hours": 0.5, "type": "break", "title": "☕ Break + Walk"},
        {"offset_hours": 3.5, "duration_hours": 1.5, "type": "admin", "title": "📋 Admin / Easy Tasks"},
        {"offset_hours": 5.0, "duration_hours": 1.0, "type": "lunch", "title": "🍽️ Lunch"},
        {"offset_hours": 6.0, "duration_hours": 1.5, "type": "creative", "title": "🎨 Low-Pressure Creative"},
        {"offset_hours": 7.5, "duration_hours": 1.0, "type": "admin", "title": "📋 Wrap Up / Planning"},
        {"offset_hours": 8.5, "duration_hours": 0.5, "type": "exercise", "title": "🚶 Light Movement / Stretching"},
        {"offset_hours": 9.5, "duration_hours": 2.0, "type": "wind_down", "title": "🌙 Early Wind Down — Prioritize Rest"},
    ],
}

# Cache settings
CACHE_FILE = "data_cache.json"
CACHE_EXPIRE_HOURS = 24
