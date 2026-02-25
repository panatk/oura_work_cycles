# Oura Smart Calendar

A self-hosted service that analyzes your Oura Ring biometric data and generates an optimized ICS calendar feed. Subscribe to the feed in Google Calendar to see personalized work block recommendations based on your actual energy and readiness patterns.

## Features

- **Biometric Analysis**: Pulls sleep, readiness, and activity data from your Oura Ring
- **Pattern Recognition**: Identifies your chronotype, peak performance windows, and energy patterns
- **Smart Scheduling**: Generates daily work blocks (deep focus, creative, admin, exercise) based on your readiness
- **Calendar Integration**: Subscribe to an ICS feed in Google Calendar for daily guidance
- **Self-Hosted**: Deploy to Railway, Render, or any free-tier host

## Privacy & Data

### Privacy Policy

This application is a **personal, self-hosted project**. It:

- **Only accesses YOUR data**: Uses your Oura Personal Access Token or OAuth credentials to fetch only your personal biometric data
- **No data sharing**: Your data is never shared, sold, or transferred to any third parties
- **Local storage**: Data is cached locally in JSON files for 60 days (per Oura API terms)
- **No analytics**: No usage tracking, analytics, or profiling
- **Secure transmission**: All API calls use HTTPS encryption

Your data is yours alone. This project respects your privacy and Oura's API terms.

### Terms of Service

By using this application, you agree to:

1. **Oura API Compliance**: Your use complies with [Oura's API Agreement](https://devs.ouraring.com/legal/api-agreement)
2. **Personal Use Only**: This application is for your personal use only
3. **Your Responsibility**: You are responsible for keeping your Oura credentials and environment variables secure
4. **No Warranty**: This project is provided as-is, without warranty of any kind
5. **Limitations**: This project is not affiliated with or endorsed by Oura, Inc.

## Getting Started

### Prerequisites

- Python 3.11+
- An Oura account with an active Ring
- Your Oura Personal Access Token or OAuth credentials

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/panatk/oura_work_cycles.git
   cd oura_work_cycles
   ```

2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env and add your OURA_TOKEN or OAuth credentials
   ```

5. Run the server:
   ```bash
   python -m src.server
   ```

6. Subscribe to the feed in Google Calendar:
   - Open Google Calendar
   - Settings → Other calendars → Subscribe to calendar
   - Paste: `http://localhost:8000/calendar.ics`

### Deployment

Deploy to Railway, Render, or similar free-tier hosts. Set the `OURA_TOKEN` environment variable on your host.

### Local Testing

- **Calendar feed**: `http://localhost:8000/calendar.ics`
- **Health check**: `http://localhost:8000/health`
- **Status**: `http://localhost:8000/status`
- **Force refresh**: `http://localhost:8000/analyze`

## Architecture

- `src/oura_client.py` — Oura API v2 client
- `src/analyzer.py` — Pattern analysis and schedule generation
- `src/calendar_gen.py` — ICS feed generation
- `src/server.py` — HTTP server (Flask/FastAPI)
- `config.py` — Schedule templates and settings
- `requirements.txt` — Python dependencies

## Contact

For questions or issues, open an issue on this repository.

## License

Personal project. Use at your own discretion.
