"""API Client for Pool Copilot."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import aiohttp

from .const import API_BASE_URL, API_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class PoolCopilotApiClient:
    """Pool Copilot API Client."""

    def __init__(self, api_key: str) -> None:
        """Initialize the API client."""
        self._api_key = api_key
        self._session: aiohttp.ClientSession | None = None
        self._base_url = API_BASE_URL
        self._token: str | None = None
        self._token_timestamp: float | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _get_token(self, force_refresh: bool = False) -> str:
        """Get authentication token from API."""
        # Check if token exists and is still valid (less than 15 minutes old)
        if self._token and self._token_timestamp and not force_refresh:
            token_age = time.time() - self._token_timestamp
            if token_age < 900:  # 15 minutes (refresh more frequently to avoid expiration)
                return self._token
            _LOGGER.debug("Token expired (age: %.0f seconds), refreshing", token_age)

        session = await self._get_session()
        url = f"{self._base_url}/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {"APIKEY": self._api_key}

        try:
            async with asyncio.timeout(API_TIMEOUT):
                async with session.post(url, headers=headers, data=data) as response:
                    response.raise_for_status()
                    result = await response.json()
                    self._token = result["token"]
                    self._token_timestamp = time.time()
                    _LOGGER.debug("Successfully obtained authentication token")
                    return self._token
        except aiohttp.ClientError as err:
            _LOGGER.error("Failed to obtain token: %s", err)
            raise
        except KeyError as err:
            _LOGGER.error("Token not found in response")
            raise

    async def _request(
        self,
        method: str,
        endpoint: str,
        retry: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make API request with automatic token refresh on expiration."""
        token = await self._get_token()
        url = f"{self._base_url}/{endpoint}"
        headers = {
            "PoolCop-Token": token,
            "Content-Type": "application/json",
        }

        session = await self._get_session()
        
        try:
            async with asyncio.timeout(API_TIMEOUT):
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    **kwargs,
                ) as response:
                    # Check for token expiration errors (403, 404, 429)
                    if response.status in (403, 404, 429) and retry:
                        _LOGGER.warning("Received %s status, attempting token refresh and retry", response.status)
                        # Force refresh token and retry - don't try to parse response
                        await self._get_token(force_refresh=True)
                        return await self._request(method, endpoint, retry=False, **kwargs)
                    
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientResponseError as err:
            # If we get a 403/404/429 during raise_for_status and haven't retried yet
            if err.status in (403, 404, 429) and retry:
                _LOGGER.warning("Got %s error, refreshing token and retrying", err.status)
                await self._get_token(force_refresh=True)
                return await self._request(method, endpoint, retry=False, **kwargs)
            _LOGGER.error("API request failed: %s", err)
            raise
        except aiohttp.ClientError as err:
            _LOGGER.error("API request failed: %s", err)
            raise
        except asyncio.TimeoutError as err:
            _LOGGER.error("API request timed out")
            raise

    async def async_get_status(self) -> dict[str, Any]:
        """Get pool status from API."""
        return await self._request("GET", "status")

    async def async_set_pump(self, turn_on: bool, speed: int | None = None) -> dict[str, Any]:
        """Turn pump on or off with optional speed setting."""
        if turn_on:
            if speed is not None:
                endpoint = f"command/pump/{speed}"
            else:
                endpoint = "command/pump"
        else:
            endpoint = "command/pump"
        
        return await self._request("POST", endpoint)

    async def async_set_aux(self, aux_id: int) -> dict[str, Any]:
        """Toggle auxiliary on or off."""
        endpoint = f"command/aux/{aux_id}"
        return await self._request("POST", endpoint)

    async def close(self) -> None:
        """Close the API session."""
        if self._session and not self._session.closed:
            await self._session.close()
