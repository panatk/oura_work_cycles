"""Oura API v2 client for fetching biometric data."""

import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

from config import (
    OURA_API_BASE,
    OURA_API_VERSION,
    OURA_TOKEN,
    OURA_CLIENT_ID,
    OURA_CLIENT_SECRET,
    OURA_HISTORY_DAYS,
)

logger = logging.getLogger(__name__)


class OuraClient:
    """Client for Oura Ring API v2."""

    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize the Oura client.

        Args:
            access_token: OAuth2 access token. If not provided, uses OURA_TOKEN env var.
        """
        self.access_token = access_token or OURA_TOKEN
        if not self.access_token:
            raise ValueError(
                "No Oura access token provided. Set OURA_TOKEN or OURA_CLIENT_ID/SECRET env vars."
            )
        self.base_url = f"{OURA_API_BASE}/{OURA_API_VERSION}"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
        )

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a GET request to the Oura API."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Oura API request failed: {e}")
            raise

    def get_daily_readiness(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch daily readiness data.

        Args:
            start_date: ISO format date (YYYY-MM-DD). Defaults to 90 days ago.
            end_date: ISO format date (YYYY-MM-DD). Defaults to today.

        Returns:
            List of daily readiness records.
        """
        if not end_date:
            end_date = datetime.utcnow().date().isoformat()
        if not start_date:
            start_date = (
                datetime.utcnow().date() - timedelta(days=OURA_HISTORY_DAYS)
            ).isoformat()

        logger.info(f"Fetching readiness data from {start_date} to {end_date}")
        data = self._get(
            "/usercollection/daily_readiness",
            params={"start_date": start_date, "end_date": end_date},
        )
        return data.get("data", [])

    def get_daily_sleep(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch daily sleep data.

        Args:
            start_date: ISO format date (YYYY-MM-DD). Defaults to 90 days ago.
            end_date: ISO format date (YYYY-MM-DD). Defaults to today.

        Returns:
            List of daily sleep records.
        """
        if not end_date:
            end_date = datetime.utcnow().date().isoformat()
        if not start_date:
            start_date = (
                datetime.utcnow().date() - timedelta(days=OURA_HISTORY_DAYS)
            ).isoformat()

        logger.info(f"Fetching sleep data from {start_date} to {end_date}")
        data = self._get(
            "/usercollection/daily_sleep",
            params={"start_date": start_date, "end_date": end_date},
        )
        return data.get("data", [])

    def get_daily_activity(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch daily activity data.

        Args:
            start_date: ISO format date (YYYY-MM-DD). Defaults to 90 days ago.
            end_date: ISO format date (YYYY-MM-DD). Defaults to today.

        Returns:
            List of daily activity records.
        """
        if not end_date:
            end_date = datetime.utcnow().date().isoformat()
        if not start_date:
            start_date = (
                datetime.utcnow().date() - timedelta(days=OURA_HISTORY_DAYS)
            ).isoformat()

        logger.info(f"Fetching activity data from {start_date} to {end_date}")
        data = self._get(
            "/usercollection/daily_activity",
            params={"start_date": start_date, "end_date": end_date},
        )
        return data.get("data", [])

    def get_sleep_periods(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch detailed sleep periods (with bedtime/wake time).

        Args:
            start_date: ISO format date (YYYY-MM-DD). Defaults to 90 days ago.
            end_date: ISO format date (YYYY-MM-DD). Defaults to today.

        Returns:
            List of sleep period records.
        """
        if not end_date:
            end_date = datetime.utcnow().date().isoformat()
        if not start_date:
            start_date = (
                datetime.utcnow().date() - timedelta(days=OURA_HISTORY_DAYS)
            ).isoformat()

        logger.info(f"Fetching sleep periods from {start_date} to {end_date}")
        data = self._get(
            "/usercollection/sleep",
            params={"start_date": start_date, "end_date": end_date},
        )
        return data.get("data", [])

    def get_all_data(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch all biometric data at once.

        Returns:
            Dictionary with keys: readiness, sleep, activity, sleep_periods
        """
        return {
            "readiness": self.get_daily_readiness(start_date, end_date),
            "sleep": self.get_daily_sleep(start_date, end_date),
            "activity": self.get_daily_activity(start_date, end_date),
            "sleep_periods": self.get_sleep_periods(start_date, end_date),
        }
