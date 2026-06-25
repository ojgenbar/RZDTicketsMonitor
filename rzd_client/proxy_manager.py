import asyncio
import logging
import socket
import time
import uuid

import aiohttp

from . import config

logger = logging.getLogger(config.LOGGER_NAME)

FETCH_COOLDOWN = 10


def _get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
    except Exception:
        logger.warning('Failed to get local IP address, falling back to 127.0.0.1')
        ip = '127.0.0.1'
    logger.info('Local IP address: %s', ip)
    return ip


class ProxyManager:
    def __init__(self, api_url: str, device_id: str):
        self._api_url = api_url
        self._device_id = device_id
        self._device_ip = _get_local_ip()
        self._proxies: list[tuple[str, str]] = []
        self._credentials: tuple[str, str] | None = None
        self._last_fetch: float = 0
        self._session: aiohttp.ClientSession | None = None
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(connect=config.CONNECT_TIMEOUT, total=config.REQUEST_TIMEOUT)
        self._session = aiohttp.ClientSession(headers=config.HEADERS_PROXY, timeout=timeout)
        await self._fetch()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._session.close()

    @property
    def proxy_url(self) -> str | None:
        if not self._proxies:
            return None
        host, port = self._proxies[0]
        if self._credentials:
            login, password = self._credentials
            return f'http://{login}:{password}@{host}:{port}'
        return f'http://{host}:{port}'

    async def on_failure(self):
        async with self._lock:
            if self._proxies:
                failed = self._proxies.pop(0)
                logger.warning(f'Proxy {failed[0]}:{failed[1]} removed after failure. {len(self._proxies)} remaining.')
            if not self._proxies:
                await self._maybe_fetch()

    async def _maybe_fetch(self):
        if time.monotonic() - self._last_fetch >= FETCH_COOLDOWN:
            await self._fetch()
            await asyncio.sleep(1)
        else:
            logger.warning('Proxy list exhausted but fetch cooldown active, no proxies available.')

    async def _fetch(self):
        payload = {
            'deviceId': self._device_id,
            # 'deviceIp': self._device_ip,
            # 'publicRequestId': str(uuid.uuid4()),
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
        self._proxies = [(p['host'], p['port']) for p in data['proxies']]
        creds = data['userProxyCredentials']
        self._credentials = (creds['login'], creds['password'])
        self._last_fetch = time.monotonic()
        logger.info(f'Fetched {len(self._proxies)} proxies.')
