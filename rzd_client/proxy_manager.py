import asyncio
import logging
import time

import aiohttp

from . import config

logger = logging.getLogger(config.LOGGER_NAME)

FETCH_COOLDOWN = 10
FAILURE_THRESHOLD = 3


class ProxyManager:
    def __init__(self, api_url: str, device_id: str):
        self._api_url = api_url
        self._device_id = device_id
        self._proxies: dict[str, None] = {}
        self._failure_counts: dict[str, int] = {}
        self._credentials: tuple[str, str] | None = None
        self._last_fetch: float = 0
        self._session: aiohttp.ClientSession | None = None
        self._lock = asyncio.Lock()
        self._fetch_lock = asyncio.Lock()

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(connect=config.CONNECT_TIMEOUT, total=config.REQUEST_TIMEOUT)
        self._session = aiohttp.ClientSession(headers=config.HEADERS_PROXY, timeout=timeout)
        await self._fetch()
        if not self._proxies:
            await self._session.close()
            raise RuntimeError(
                f'Initial proxy fetch from {self._api_url} failed or returned no proxies'
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._session.close()

    @property
    def proxy_url(self) -> str | None:
        endpoint = self.proxy_endpoint
        if endpoint is None:
            return None
        if self._credentials:
            login, password = self._credentials
            return f'http://{login}:{password}@{endpoint}'
        return f'http://{endpoint}'

    @property
    def proxy_endpoint(self) -> str | None:
        return next(iter(self._proxies), None)

    def on_success(self, endpoint: str):
        self._failure_counts.pop(endpoint, None)

    async def on_failure(self, endpoint: str):
        async with self._lock:
            if endpoint not in self._proxies:
                logger.info(f'Proxy {endpoint} already removed by another task.')
                need_fetch = not self._proxies
            else:
                count = self._failure_counts.get(endpoint, 0) + 1
                self._failure_counts[endpoint] = count
                if count >= FAILURE_THRESHOLD:
                    del self._proxies[endpoint]
                    self._failure_counts.pop(endpoint, None)
                    logger.warning(
                        f'Proxy {endpoint} removed after {FAILURE_THRESHOLD} consecutive failures. '
                        f'{len(self._proxies)} remaining.'
                    )
                else:
                    logger.warning(f'Proxy {endpoint} failure {count}/{FAILURE_THRESHOLD}.')
                need_fetch = not self._proxies
        if need_fetch:
            await self._maybe_fetch()

    async def _maybe_fetch(self):
        async with self._fetch_lock:
            if time.monotonic() - self._last_fetch >= FETCH_COOLDOWN:
                await self._fetch()
            else:
                logger.warning('Proxy list exhausted but fetch cooldown active, no proxies available.')

    async def _fetch(self):
        payload = {
            'deviceId': self._device_id,
        }
        logger.info(f'Fetching proxy list from {self._api_url}')
        try:
            async with self._session.post(self._api_url, json=payload) as resp:
                if resp.status != 200:
                    logger.error(f'Proxy API returned status {resp.status}: {await resp.text()}')
                    return
                data = await resp.json()
        except Exception as e:
            logger.error(f'Failed to fetch proxy list: {repr(e)}')
            return
        self._proxies = {f"{p['host']}:{p['port']}": None for p in data['proxies']}
        creds = data['userProxyCredentials']
        self._credentials = (creds['login'], creds['password'])
        self._last_fetch = time.monotonic()
        logger.info(f'Fetched {len(self._proxies)} proxies.')
