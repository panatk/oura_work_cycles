"""Pattern analyzer for Oura data and schedule generation."""

import logging
import json
from datetime import datetime, time, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

import pytz

from config import (
    TIMEZONE,
    HIGH_ENERGY_THRESHOLD,
    RECOVERY_THRESHOLD,
    SCHEDULE_TEMPLATES,
)

logger = logging.getLogger(__name__)


class OuraAnalyzer:
    """Analyzes Oura data patterns and generates personalized schedules."""

    def __init__(self):
        self.tz = pytz.timezone(TIMEZONE)
        self.patterns = {
            "chronotype": None,
            "average_wake_time": None,
            "average_bedtime": None,
            "peak_focus_window": None,
            "day_of_week_patterns": {},
        }

    def analyze_historical_data(self, data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Analyze 90-day historical data to determine patterns.

        Args:
            data: Dictionary with keys readiness, sleep, activity, sleep_periods

        Returns:
            Patterns dictionary with chronotype, peak windows, and day-of-week stats.
        """
        readiness = data.get("readiness", [])
        sleep_periods = data.get("sleep_periods", [])

        if not readiness or not sleep_periods:
            logger.warning("Insufficient data for historical analysis")
            return self.patterns

        # Chronotype detection from sleep periods
        self._analyze_chronotype(sleep_periods)

        # Day of week patterns
        self._analyze_day_of_week_patterns(readiness)

        logger.info(f"Historical analysis complete. Patterns: {self.patterns}")
        return self.patterns

    def _analyze_chronotype(self, sleep_periods: List[Dict[str, Any]]) -> None:
        """Determine chronotype from average bedtime and wake time."""
        if not sleep_periods:
            return

        wake_times = []
        bed_times = []

        for period in sleep_periods:
            try:
                if "bedtime_start" in period and "bedtime_end" in period:
                    bed_time_str = period["bedtime_start"]
                    wake_time_str = period["bedtime_end"]

                    bed_dt = datetime.fromisoformat(bed_time_str.replace("Z", "+00:00"))
                    wake_dt = datetime.fromisoformat(wake_time_str.replace("Z", "+00:00"))

                    # Convert to local timezone
                    bed_local = bed_dt.astimezone(self.tz).time()
                    wake_local = wake_dt.astimezone(self.tz).time()

                    bed_times.append(bed_local)
                    wake_times.append(wake_local)
            except Exception as e:
                logger.debug(f"Error parsing sleep period: {e}")
                continue

        if wake_times:
            avg_wake_minutes = sum(
                t.hour * 60 + t.minute for t in wake_times
            ) / len(wake_times)
            avg_wake_time = time(int(avg_wake_minutes // 60), int(avg_wake_minutes % 60))
            self.patterns["average_wake_time"] = avg_wake_time.isoformat()

            # Classify chronotype
            wake_hour = int(avg_wake_minutes // 60)
            if wake_hour < 6:
                chronotype = "early"
            elif wake_hour < 8:
                chronotype = "moderate"
            else:
                chronotype = "late"
            self.patterns["chronotype"] = chronotype

        if bed_times:
            # Handle bedtimes that cross midnight (00:XX times treated as 24:XX)
            bed_minutes_list = []
            for t in bed_times:
                minutes = t.hour * 60 + t.minute
                # If bedtime is early morning (before 6 AM), treat as previous day (add 24 hours)
                if t.hour < 6:
                    minutes += 24 * 60
                bed_minutes_list.append(minutes)

            avg_bed_minutes = sum(bed_minutes_list) / len(bed_minutes_list)
            # Handle wraparound: if over 24 hours, subtract 24 hours
            if avg_bed_minutes >= 24 * 60:
                avg_bed_minutes -= 24 * 60

            avg_bed_time = time(int(avg_bed_minutes // 60), int(avg_bed_minutes % 60))
            self.patterns["average_bedtime"] = avg_bed_time.isoformat()

        logger.info(
            f"Chronotype: {self.patterns['chronotype']}, "
            f"Avg wake: {self.patterns['average_wake_time']}, "
            f"Avg bed: {self.patterns['average_bedtime']}"
        )

    def _analyze_day_of_week_patterns(self, readiness: List[Dict[str, Any]]) -> None:
        """Analyze readiness by day of week."""
        day_readiness = defaultdict(list)

        for record in readiness:
            try:
                date_str = record.get("day")
                score = record.get("score")
                if date_str and score:
                    date_obj = datetime.fromisoformat(date_str)
                    day_name = date_obj.strftime("%A")
                    day_readiness[day_name].append(score)
            except Exception as e:
                logger.debug(f"Error processing readiness record: {e}")
                continue

        # Calculate averages per day
        for day, scores in day_readiness.items():
            avg_score = sum(scores) / len(scores)
            self.patterns["day_of_week_patterns"][day] = {
                "average_readiness": round(avg_score, 1),
                "samples": len(scores),
            }

        logger.info(f"Day of week patterns: {self.patterns['day_of_week_patterns']}")

    def get_energy_archetype(self, readiness_score: float) -> str:
        """
        Classify energy level based on readiness score.

        Args:
            readiness_score: Readiness score (0-100)

        Returns:
            "high_energy", "normal", or "recovery"
        """
        if readiness_score >= HIGH_ENERGY_THRESHOLD:
            return "high_energy"
        elif readiness_score >= RECOVERY_THRESHOLD:
            return "normal"
        else:
            return "recovery"

    def generate_daily_schedule(
        self,
        readiness_score: float,
        wake_time: Optional[datetime] = None,
        today_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate today's schedule based on readiness and wake time.

        Args:
            readiness_score: Today's readiness score
            wake_time: Actual wake time (if available from sleep data)
            today_date: Today's date (defaults to now)

        Returns:
            List of time blocks with start, end, type, and description.
        """
        if today_date is None:
            today_date = datetime.now(self.tz)

        # If no wake time provided, use average from patterns or estimate
        if wake_time is None:
            if self.patterns.get("average_wake_time"):
                avg_wake_str = self.patterns["average_wake_time"]
                parts = avg_wake_str.split(":")
                wake_hour = int(parts[0])
                wake_min = int(parts[1])
                wake_time = today_date.replace(hour=wake_hour, minute=wake_min, second=0, microsecond=0)
            else:
                # Default to 6 AM if no pattern data
                wake_time = today_date.replace(hour=6, minute=0, second=0, microsecond=0)

        # Get archetype and template
        archetype = self.get_energy_archetype(readiness_score)
        template = SCHEDULE_TEMPLATES.get(archetype, SCHEDULE_TEMPLATES["normal"])

        # Generate blocks
        schedule = []
        for block_template in template:
            block_start_time = wake_time + timedelta(
                hours=block_template["offset_hours"]
            )
            block_end_time = block_start_time + timedelta(
                hours=block_template["duration_hours"]
            )

            schedule.append(
                {
                    "start": block_start_time,
                    "end": block_end_time,
                    "type": block_template["type"],
                    "title": block_template["title"],
                    "description": self._get_block_description(
                        block_template["type"], archetype, readiness_score
                    ),
                    "readiness_score": readiness_score,
                    "archetype": archetype,
                }
            )

        logger.info(f"Generated {len(schedule)} schedule blocks for {archetype} day")
        return schedule

    def _get_block_description(
        self, block_type: str, archetype: str, readiness_score: float
    ) -> str:
        """Generate a description for a schedule block."""
        descriptions = {
            "deep_focus": f"Focus time for your most important work. Readiness: {readiness_score:.0f}. Level: {archetype.replace('_', ' ').title()}.",
            "creative": "Creative and collaborative work block.",
            "admin": "Administrative tasks, email, and meetings.",
            "exercise": "Physical activity and movement.",
            "break": "Rest and recovery.",
            "lunch": "Meal break.",
            "morning_routine": "Start your day with intention.",
            "wind_down": "Prepare for quality sleep.",
        }
        return descriptions.get(block_type, f"{block_type.replace('_', ' ').title()} block.")
