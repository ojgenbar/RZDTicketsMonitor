import json
import logging
import typing

import aiohttp
from aiohttp import hdrs

from . import config
from . import common
from . import models
from .proxy_manager import ProxyManager


logger = logging.getLogger(config.LOGGER_NAME)


class RZDClient:
    def __init__(self):
        self._session: typing.Optional[aiohttp.ClientSession] = None
        self._proxy_manager: typing.Optional[ProxyManager] = None

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(connect=config.CONNECT_TIMEOUT, total=config.REQUEST_TIMEOUT)
        self._session = aiohttp.ClientSession(headers=config.HEADERS, timeout=timeout)
        if config.PROXY_API_URL:
            logger.info(f'Proxy url detected. Starting the proxy manager, url: {config.PROXY_API_URL}')
            self._proxy_manager = ProxyManager(config.PROXY_API_URL, config.PROXY_API_DEVICE_ID)
            await self._proxy_manager.__aenter__()
        else:
            logger.info(f'No proxy url detected')
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._proxy_manager:
            await self._proxy_manager.__aexit__(exc_type, exc_val, exc_tb)
            logger.info(f'Proxy manager closed')
        await self._session.close()

    async def fetch_station_suggests(self, string: str, lang: str = 'ru') -> dict:
        if len(string) < 2:
            message = (
                f'String must contain at least 2 char. '
                f'Got: {len(string)} for "{string}"'
            )
            raise ValueError(message)
        string = string.strip()[:2].upper()
        return await self._fetch_station_suggests_raw(string, lang)

    async def _fetch_station_suggests_raw(self, string: str, lang: str) -> dict:
        params = {'stationNamePart': string, 'lang': lang}
        data = await common.rzd_request(
            self._session,
            hdrs.METH_GET,
            url=config.SUGGESTS_BASE_URL,
            proxy_manager=self._proxy_manager,
            params=params
        )
        if not data:
            return {}

        suggests_dict = {}
        for doc in data:
            suggests_dict[doc['n']] = doc['c']
        logger.debug(
            'Suggests data: {}'.format(
                json.dumps(suggests_dict, ensure_ascii=False),
            ),
        )
        return suggests_dict

    async def fetch_train_detailed(self, args: models.TrainDetailedRequestArgs) -> models.TrainOverview:
        data = await common.rzd_rid_request(
            session=self._session,
            url=config.BASE_URL,
            args=args.as_rzd_args(),
            proxy_manager=self._proxy_manager,
        )
        train = models.TrainDetailed.from_rzd_json(data['lst'][0])
        return train

    async def fetch_trains_overview(self, args: models.TrainsOverviewRequestArgs) -> typing.List[models.TrainOverview]:
        data = await common.rzd_rid_request(
            session=self._session,
            url=config.SUGGEST_TRAINS_URL,
            args=args.as_rzd_args(),
            proxy_manager=self._proxy_manager,
        )

        trains = [
            models.TrainOverview.from_rzd_json(raw)
            for raw in data['tp'][0]['list']
        ]
        return trains
