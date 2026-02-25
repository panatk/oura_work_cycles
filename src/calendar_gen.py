"""ICS calendar feed generator from schedule blocks."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

import pytz
from icalendar import Calendar, Event

from config import TIMEZONE

logger = logging.getLogger(__name__)


class CalendarGenerator:
    """Generates ICS calendar feeds from schedule blocks."""

    def __init__(self):
        self.tz = pytz.timezone(TIMEZONE)

    def generate_ics(self, schedule_blocks: List[Dict[str, Any]]) -> str:
        """
        Generate ICS calendar feed from schedule blocks.

        Args:
            schedule_blocks: List of schedule blocks with start, end, title, description, etc.

        Returns:
            ICS calendar string.
        """
        cal = Calendar()
        cal.add("prodid", "-//Oura Smart Calendar//panatk//EN")
        cal.add("version", "2.0")
        cal.add("calscale", "GREGORIAN")
        cal.add("method", "PUBLISH")
        cal.add("x-wr-calname", "Oura Smart Calendar")
        cal.add(
            "x-wr-description",
            "Personalized work blocks based on your Oura Ring biometric data",
        )
        cal.add("x-wr-timezone", TIMEZONE)

        # Create events from blocks
        for block in schedule_blocks:
            event = self._create_event(block)
            cal.add_component(event)

        ics_output = cal.to_ical().decode("utf-8")
        logger.info(f"Generated ICS feed with {len(schedule_blocks)} events")
        return ics_output

    def _create_event(self, block: Dict[str, Any]) -> Event:
        """Create a VEVENT from a schedule block."""
        event = Event()

        # Ensure times are timezone-aware
        start = block["start"]
        end = block["end"]

        if start.tzinfo is None:
            start = self.tz.localize(start)
        if end.tzinfo is None:
            end = self.tz.localize(end)

        event.add("summary", block["title"])
        event.add("dtstart", start)
        event.add("dtend", end)
        event.add("description", block.get("description", ""))
        event.add("categories", [block.get("type", "work")])
        event.add("transp", "TRANSPARENT")  # Don't block calendar time
        event.add("location", "")

        # Add UID (required)
        uid = f"{start.isoformat()}--{block.get('type', 'event')}@ouraring-calendar"
        event.add("uid", uid)

        # Add created/modified timestamps
        now = datetime.now(self.tz)
        event.add("created", now)
        event.add("last-modified", now)

        # Add color categories
        color_map = {
            "deep_focus": "blue",
            "creative": "purple",
            "admin": "orange",
            "exercise": "green",
            "break": "yellow",
            "lunch": "brown",
            "morning_routine": "pink",
            "wind_down": "indigo",
        }
        color = color_map.get(block.get("type"), "blue")
        event.add("x-microsoft-cdo-busystatus", "FREE")
        event.add("x-microsoft-cdo-importance", "normal")

        return event

    def generate_multi_day_ics(
        self, analyzer, oura_client, days_ahead: int = 7
    ) -> str:
        """
        Generate ICS feed for today + next N days.

        Args:
            analyzer: OuraAnalyzer instance
            oura_client: OuraClient instance
            days_ahead: Number of days to generate (including today)

        Returns:
            ICS calendar string.
        """
        cal = Calendar()
        cal.add("prodid", "-//Oura Smart Calendar//panatk//EN")
        cal.add("version", "2.0")
        cal.add("calscale", "GREGORIAN")
        cal.add("method", "PUBLISH")
        cal.add("x-wr-calname", "Oura Smart Calendar")
        cal.add(
            "x-wr-description",
            "Personalized work blocks based on your Oura Ring biometric data",
        )
        cal.add("x-wr-timezone", TIMEZONE)

        # Get today's readiness for context
        today_date = datetime.now(self.tz).date()
        event_count = 0

        for day_offset in range(days_ahead):
            target_date = today_date + timedelta(days=day_offset)
            target_date_str = target_date.isoformat()

            # Try to get actual readiness data
            readiness_score = 70  # Default fallback

            # Generate schedule
            target_datetime = datetime.combine(target_date, datetime.min.time())
            target_datetime = self.tz.localize(target_datetime)

            schedule = analyzer.generate_daily_schedule(
                readiness_score=readiness_score,
                wake_time=None,
                today_date=target_datetime,
            )

            # Add events to calendar
            for block in schedule:
                event = self._create_event(block)
                cal.add_component(event)
                event_count += 1

        ics_output = cal.to_ical().decode("utf-8")
        logger.info(f"Generated multi-day ICS feed with {event_count} events")
        return ics_output
