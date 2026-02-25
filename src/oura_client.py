"""Oura API v2 client for fetching biometric data."""

import logging
import requests
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from pathlib import Path

from config import (
    OURA_API_BASE,
    OURA_API_VERSION,
    OURA_TOKEN,
    OURA_CLIENT_ID,
    OURA_CLIENT_SECRET,
    OURA_REDIRECT_URI,
    OURA_HISTORY_DAYS,
)

logger = logging.getLogger(__name__)

TOKEN_CACHE_FILE = "oura_token_cache.json"


class OuraClient:
    """Client for Oura Ring API v2."""

    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize the Oura client.

        Args:
            access_token: OAuth2 access token. If not provided, tries:
                         1. OURA_TOKEN env var
                         2. OAuth2 exchange with OURA_CLIENT_ID/SECRET
                         3. Cached token from previous authorization
        """
        self.access_token = access_token or OURA_TOKEN

        # If no direct token, try OAuth2
        if not self.access_token:
            if OURA_CLIENT_ID and OURA_CLIENT_SECRET:
                logger.info("No direct token found. Attempting OAuth2 token exchange...")
                self.access_token = self._get_oauth2_token()
            else:
                raise ValueError(
                    "No Oura credentials provided. Set OURA_TOKEN or OURA_CLIENT_ID/SECRET env vars."
                )

        if not self.access_token:
            raise ValueError("Failed to obtain Oura access token")

        self.base_url = f"{OURA_API_BASE}/{OURA_API_VERSION}"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
        )

    def _get_oauth2_token(self) -> Optional[str]:
        """
        Try to use a cached token. If not available, return None and user must authorize.

        Returns:
            Access token string, or None if no cached token exists.
        """
        # First check if we have a cached token
        if Path(TOKEN_CACHE_FILE).exists():
            cached = self._load_cached_token()
            if cached:
                logger.info("Using cached Oura access token")
                return cached

        logger.warning(
            "No cached token found. User must authorize via /authorize endpoint first."
        )
        return None

    @staticmethod
    def exchange_auth_code(auth_code: str) -> Optional[str]:
        """
        Exchange authorization code for access token.

        Args:
            auth_code: Authorization code from Oura OAuth redirect

        Returns:
            Access token string, or None if exchange fails.
        """
        try:
            token_url = f"{OURA_API_BASE}/oauth/token"

            payload = {
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": OURA_CLIENT_ID,
                "client_secret": OURA_CLIENT_SECRET,
                "redirect_uri": OURA_REDIRECT_URI,
            }

            logger.info(f"Exchanging auth code for token at {token_url}")
            # Use form data (application/x-www-form-urlencoded) instead of JSON
            response = requests.post(token_url, data=payload, timeout=10)

            try:
                data = response.json()
            except:
                data = response.text

            if response.status_code == 200:
                token = data.get("access_token")
                if token:
                    OuraClient._save_cached_token_static(token, data.get("expires_in"))
                    logger.info("Successfully obtained Oura access token via OAuth2")
                    return token
                else:
                    logger.error(f"No access token in response: {data}")
                    return None
            else:
                logger.error(f"Token exchange error ({response.status_code}): {data}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Token exchange failed: {e}")
            return None

    def _load_cached_token(self) -> Optional[str]:
        """Load cached token if it hasn't expired."""
        try:
            with open(TOKEN_CACHE_FILE, 'r') as f:
                cache = json.load(f)
                expires_at = cache.get("expires_at")
                if expires_at and datetime.now().timestamp() < expires_at:
                    return cache.get("token")
        except Exception as e:
            logger.debug(f"Could not load cached token: {e}")
        return None

    @staticmethod
    def _save_cached_token_static(token: str, expires_in: Optional[int] = None) -> None:
        """Save token to cache file."""
        try:
            expires_at = None
            if expires_in:
                expires_at = (datetime.now().timestamp()) + expires_in - 300  # Refresh 5 min early

            cache = {
                "token": token,
                "expires_at": expires_at,
                "cached_at": datetime.now().isoformat(),
            }
            with open(TOKEN_CACHE_FILE, 'w') as f:
                json.dump(cache, f)
            logger.debug(f"Cached Oura token (expires at: {expires_at})")
        except Exception as e:
            logger.warning(f"Could not cache token: {e}")

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
