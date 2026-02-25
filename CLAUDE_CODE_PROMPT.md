# Oura → Smart Calendar Project

## Goal

Build a self-hosted service that pulls my Oura Ring data, analyzes my energy/readiness patterns, and serves a subscribable ICS calendar feed that overlays optimized work blocks onto my day. I subscribe to this in Google Calendar and it tells me what type of work I should be doing and when, based on my actual biometric patterns.

## Architecture

Simple Python project. Minimal dependencies. Deployable to Railway, Render, or any free-tier host that can run a small web server.

```
oura-calendar/
├── README.md
├── requirements.txt
├── .env.example          # OURA_TOKEN=your_token_here
├── src/
│   ├── oura_client.py    # Oura API v2 client
│   ├── analyzer.py       # Pattern analysis & schedule generation
│   ├── calendar_gen.py   # ICS feed generation
│   └── server.py         # Lightweight HTTP server (Flask or FastAPI)
├── config.py             # Schedule templates, thresholds, timezone
└── tests/
```

## Step-by-step Plan

### 1. Oura API Client (`oura_client.py`)

- Use Oura API v2: https://cloud.ouraring.com/v2/docs
- Auth via Personal Access Token (stored in `OURA_TOKEN` env var)
- Fetch these endpoints for the last 90 days:
  - `GET /v2/usercollection/daily_readiness` — readiness score, HRV balance, temperature deviation
  - `GET /v2/usercollection/daily_sleep` — sleep score, deep sleep duration, REM, total sleep, efficiency
  - `GET /v2/usercollection/daily_activity` — activity score, steps, active calories
  - `GET /v2/usercollection/sleep` — detailed sleep periods with bedtime/wake time
- Also fetch today's data for the daily calendar generation
- Handle pagination if needed
- Cache the 90-day historical data (refresh once per day) — a simple JSON file cache is fine

### 2. Pattern Analyzer (`analyzer.py`)

This is the brain of the project. Two responsibilities:

#### A. Historical Pattern Analysis (runs once on setup, refreshes weekly)

Analyze the 90-day historical data to determine:

1. **Chronotype detection**: What's my average bedtime, wake time, and sleep midpoint? Classify as early, moderate, or late chronotype.

2. **Peak performance windows**: Based on wake time + chronotype research, estimate:
   - **Deep focus window**: Typically 2-4 hours after waking (highest cortisol + alertness)
   - **Creative window**: Typically early afternoon when associative thinking peaks
   - **Admin/meetings window**: Mid-afternoon energy dip — good for routine tasks
   - **Exercise window**: Based on temperature and activity patterns

3. **Energy archetypes**: Cluster my days into 3 tiers based on readiness score:
   - **High energy day** (readiness ≥ 85): Full deep work schedule, ambitious tasks
   - **Normal day** (readiness 70-84): Standard schedule
   - **Recovery day** (readiness < 70): Lighter schedule, more breaks, admin-heavy

4. **Day-of-week patterns**: Do I consistently have lower readiness on certain days? (e.g., post-weekend, mid-week dip)

Store these derived patterns in a config/JSON so the daily generator can use them.

#### B. Daily Schedule Generation (runs each morning)

- Pull today's readiness score, last night's sleep data
- Select the appropriate energy archetype (high/normal/recovery)
- Adjust time blocks based on actual wake time (if available from sleep data)
- Generate the day's schedule as a list of time blocks, each with:
  - Start/end time
  - Block type (deep_focus, creative, admin, exercise, break, wind_down)
  - Title and description with context (e.g., "Deep Focus — High energy day, prioritize your hardest task")
  - Color category suggestion

### 3. Schedule Templates (`config.py`)

Define the templates here so I can easily tweak them:

```python
TIMEZONE = "Australia/Sydney"  # User's timezone

# These offsets are relative to wake time
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

# Readiness thresholds
HIGH_ENERGY_THRESHOLD = 85
RECOVERY_THRESHOLD = 70
```

### 4. ICS Calendar Generator (`calendar_gen.py`)

- Use the `icalendar` Python library
- Generate a VCALENDAR with events for today + next 6 days
  - Today: based on actual readiness score
  - Future days: based on day-of-week historical averages (best guess)
- Each VEVENT should include:
  - Summary (the title from template)
  - Description (include readiness score context, e.g., "Based on your readiness score of 92. This is a high energy day — make the most of this deep focus block.")
  - DTSTART / DTEND in the correct timezone
  - A CATEGORIES field for the block type
  - Use TRANSP:TRANSPARENT so these don't block out time on the calendar (they're advisory, not commitments)
- Set appropriate cache headers so Google Calendar refreshes every few hours

### 5. Web Server (`server.py`)

Minimal Flask or FastAPI server with these routes:

- `GET /calendar.ics` — returns the ICS feed (this is what Google Calendar subscribes to)
- `GET /health` — health check for deployment
- `GET /status` — JSON endpoint showing current readiness score, today's archetype, and schedule (useful for debugging)
- `GET /analyze` — triggers a re-analysis of historical patterns (manual refresh)

On startup:
1. Pull 90-day historical data
2. Run pattern analysis
3. Generate today's schedule
4. Serve the ICS feed

Use a background task or cron to refresh daily data each morning (e.g., at 6am in my timezone).

### 6. Deployment

- Include a `Dockerfile` for easy deployment
- Include a `railway.json` or `render.yaml` for one-click deploy
- The only required env var is `OURA_TOKEN`
- Optional env var: `TIMEZONE` (default to Australia/Sydney)

## Important Notes

- Use `Australia/Sydney` as the default timezone throughout
- All times in the ICS should be timezone-aware
- The ICS feed URL should be stable so Google Calendar subscription doesn't break
- Keep the server lightweight — this should run fine on a free tier
- Add good logging so I can debug issues with the Oura API or schedule generation
- Include a clear README.md explaining how to:
  1. Get an Oura Personal Access Token
  2. Set up the env vars
  3. Run locally
  4. Deploy to Railway/Render
  5. Subscribe to the feed in Google Calendar (Settings → Other calendars → From URL)

## Tech Stack

- Python 3.11+
- Flask or FastAPI (your choice, whichever is simpler)
- `icalendar` for ICS generation
- `requests` or `httpx` for Oura API
- `python-dotenv` for env vars
- No database — JSON file cache is fine
- No frontend needed

## Getting Started

```bash
# Create the project
mkdir oura-calendar && cd oura-calendar
git init

# Set up
cp .env.example .env
# Add your OURA_TOKEN to .env

# Install & run
pip install -r requirements.txt
python -m src.server
# Visit http://localhost:8080/calendar.ics
```

Build this step by step. Start with the Oura client, verify it pulls data correctly, then build the analyzer, then the calendar generator, then wire it all up with the server. Test each piece as you go.
