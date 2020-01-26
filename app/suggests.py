import asyncio
import dataclasses
import json
import logging
import collections

import typing

import aiohttp
from fuzzywuzzy import process

from app import monitor
from app.configs import rzd as config
from app.configs import messages


class StationSuggester:
    def __init__(self, string):
        self.string = string
        self.is_exact_match = None
        self.suggestions = None
        self.match_id = None

    async def fetch_station_suggests(self, string):
        if len(string) < 2:
            message = (
                f'String must contain at least 2 char. '
                f'Got: {len(string)} for "{string}"'
            )
            raise ValueError(message)
        string = string.strip()[:2].upper()
        return await self._fetch_station_suggests_raw(string)

    @staticmethod
    async def _fetch_station_suggests_raw(string):
        params = {'stationNamePart': string, 'lang': 'ru'}
        async with aiohttp.ClientSession() as session:
            response = await session.get(
                config.SUGGESTS_BASE_URL, params=params,
            )
            logging.info(
                f'Suggest request for: {string}, status={response.status}, '
                f'url={response.url}',
            )
            data = await response.json()
            assert response.status == 200
            if not data:
                return {}
            suggests_dict = {}
            for doc in data:
                suggests_dict[doc['n']] = doc['c']
            logging.info(
                'Suggest data: {}'.format(
                    json.dumps(suggests_dict, ensure_ascii=False),
                ),
            )
            return suggests_dict

    async def suggest_station(self):
        string = self.string.upper()
        suggests_dict = None
        for i in range(config.REQUEST_ATTEMPTS):
            try:
                suggests_dict = await self.fetch_station_suggests(string)
                break
            except aiohttp.ClientConnectionError:
                sleep = config.SLEEP_AFTER_UNSUCCESSFUL_REQUEST * (i + 1)
                logging.warning(
                    f'Cannot fetch suggests. Current attempt is {i+1}. '
                    f'Sleep: {sleep:.1f} sec.',
                )
                await asyncio.sleep(sleep)

        if suggests_dict is None:
            msg = 'Cannot fetch station suggests. Attempts limit is exceeded.'
            logging.error(msg)
            raise RuntimeError(msg)

        if not suggests_dict:
            self.suggestions = {}
            return
        if string in suggests_dict:
            self.is_exact_match = True
            id_ = suggests_dict[string]
            self.match_id = id_
            self.suggestions = {string: id_}
            return

        self.is_exact_match = False
        corpus = suggests_dict.keys()
        result = process.extract(string, corpus, limit=config.SUGGESTS_LIMIT)
        logging.info(f'filtered similarity request result: {repr(result)}')
        filtered_result = [
            n[0] for n in result if n[1] > config.MIN_SUGGESTS_SIMILARITY
        ]
        filtered_suggests = {k: suggests_dict[k] for k in filtered_result}
        self.suggestions = filtered_suggests


@dataclasses.dataclass
class Train:
    brand: str
    carrier: typing.Optional[str]
    departure_station_code: int  # code0
    destination_station_code: int  # code1
    number: str
    train_route: str
    time_departure: str
    time_arrival: str
    time_in_way: str
    service_categories: typing.List[str]

    @property
    def service_categories_string(self):
        if self.service_categories:
            return '*{}*'.format('*, *'.join(self.service_categories))
        else:
            return ''

    def to_message(self, template=messages.AVAILABLE_TRAINS_TEMPLATE):
        return template.format(train=self)

    @classmethod
    def from_rzd_dict(cls, data):
        categories = {
            cat['typeCarCharCode'] for cat in data['serviceCategories']
        }
        instance = cls(
            brand=data['brand'],
            carrier=data['carrier'],
            departure_station_code=data['code0'],
            destination_station_code=data['code1'],
            number=data['number'],
            train_route='{} --> {}'.format(data['route0'], data['route1']),
            time_departure=data['time0'],
            time_arrival=data['time1'],
            time_in_way=data['timeInWay'],
            service_categories=sorted(categories),
        )
        return instance


async def trains(departure, destination, date_str):
    args = {
        'dir': '0',
        'tfl': '3',
        'code0': departure,
        'code1': destination,
        'dt0': date_str,
        'checkSeats': '0',
        'withoutSeats': 'y',
        'version': '2',
        'actorType': 'desktop_2016',
    }

    async with aiohttp.ClientSession() as session:
        data = await monitor.rzd_rid_request(
            session, config.SUGGEST_TRAINS_URL, args,
        )

    trains = collections.OrderedDict()
    for train_data in data['tp'][0]['list']:
        train = Train.from_rzd_dict(train_data)
        trains[train.number] = train
    return trains
