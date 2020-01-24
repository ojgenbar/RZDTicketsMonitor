import asyncio
import datetime
import logging
import random
import traceback
import functools
from pprint import pformat, pprint
import json
import aiohttp

import config
from fuzzywuzzy import process


BASE_URL = r'https://pass.rzd.ru/timetable/public/en?layer_id=5764'
SUGGESTS_BASE_URL = r'http://www.rzd.ru/suggester'


class RZDNegativeResponse(RuntimeError):
    pass


class AsyncMonitor:
    def __init__(self, args, requested_count=1, cars_type="Плац", *,
                 delay_base=config.BASIC_DELAY_BASE, callback=None, prefix=''):
        self.args = args
        self.requested_count = requested_count
        self.cars_type = cars_type
        self.delay_base = delay_base
        self.callback = callback or self.default_callback
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0',
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        self.session = None
        self.stop = False
        self.last_message = None
        self.last_time = None
        self.log_prefix = prefix

    @staticmethod
    async def default_callback(string):
        logging.info(string)

    def get_cars(self, data):
        data = data["lst"][0]
        if data['result'] != 'OK':
            raise RZDNegativeResponse(data['error'])
        cars = data["cars"]
        filtered_cars = [c for c in cars if c['type'] == self.cars_type]
        return filtered_cars

    @staticmethod
    def get_places_count(cars):
        return sum(c["seats"][0]["free"] for c in cars)

    async def make_request(self, result_json):
        url = BASE_URL

        async with self.session.post(
                url, data=result_json, headers=self.headers
        ) as resp:
            result_json = await resp.json(content_type=None)
            logging.info(pformat(result_json).replace('\n', '\\n'))

        return result_json

    async def get_data(self):
        args = {**self.args}
        rid_data = await self.make_request(args)
        rid = str(rid_data['RID'])

        args['rid'] = rid

        await asyncio.sleep(config.SLEEP_AFTER_RID_REQUEST)

        data = await self.make_request(args)
        if data["result"] == 'RID':
            logging.warning(f'Unexpected RID result. Data: f{data}')
            data = await self.get_data()
            await asyncio.sleep(2)
        return data

    async def run(self):
        async with aiohttp.ClientSession() as self.session:
            while not self.stop:
                try:
                    data = await self.get_data()
                    cars = self.get_cars(data)
                    places = self.get_places_count(cars)
                    msg = f'Total: {places} tickets'
                    self.last_message = msg
                    self.last_time = datetime.datetime.now()
                    logging.info(f'{self.log_prefix}{msg}')
                    if places >= self.requested_count:
                        await self.callback(msg)
                except RZDNegativeResponse:
                    raise
                except Exception:
                    logging.warning(traceback.format_exc())
                finally:
                    await asyncio.sleep(5 + self.delay_base * random.random())


async def fetch_station_suggests(string):
    if len(string) < 2:
        message = (
            f'String must contain at least 2 char. '
            f'Got: {len(string)} for "{string}"'
        )
        raise ValueError(message)
    string = string.strip()[:2].upper()
    return await _fetch_station_suggests_raw(string)


# @functools.lru_cache(None)
async def _fetch_station_suggests_raw(string):
    params = {
        "stationNamePart": string,
        "lang": "ru",
    }
    async with aiohttp.ClientSession() as session:
        response = await session.get(
            SUGGESTS_BASE_URL,
            params=params,
        )
        logging.info(
            f"Suggest request for: {string}, status={response.status}, "
            f"url={response.url}"
        )
        data = await response.json()
        assert response.status == 200
        if not data:
            return {}
        suggests_dict = {}
        for doc in data:
            suggests_dict[doc['n']] = doc['c']
        logging.info("Suggest data: {}".format(
            json.dumps(suggests_dict, ensure_ascii=False)
        ))
        return suggests_dict


async def suggest_station(string):
    string = string.upper()
    suggests_dict = None
    for i in range(config.REQUEST_ATTEMPTS):
        try:
            suggests_dict = await fetch_station_suggests(string)
            break
        except aiohttp.ClientConnectionError:
            sleep = config.SLEEP_AFTER_UNSUCCESSFUL_REQUEST * (i + 1)
            logging.warning(
                f'Cannot fetch suggests. Current attempt is {i+1}. '
                f'Sleep: {sleep:.1f} sec.'
            )
            await asyncio.sleep(sleep)

    if suggests_dict is None:
        msg = 'Cannot fetch station suggests. Attempts limit is exceeded.'
        logging.error(msg)
        raise RuntimeError(msg)

    if string in suggests_dict:
        return {string: suggests_dict[string]}

    corpus = suggests_dict.keys()
    result = process.extract(string, corpus, limit=config.SUGGESTS_LIMIT)
    logging.info(f"filtered similarity request result: {repr(result)}")
    filtered_result = [
        n[0]
        for n in result
        if n[1] > config.MIN_SUGGESTS_SIMILARITY
    ]
    filtered_suggests = {k: suggests_dict[k] for k in filtered_result}
    return filtered_suggests


def main():
    import argparse

    parser = argparse.ArgumentParser(description='RZD monitor. Monitors if desired tickets are available.')
    parser.add_argument(dest='departure', type=str,
                        help='Departure station ID (e.g. "2010290")')
    parser.add_argument(dest='destination', type=str,
                        help='Destination station ID (e.g. "2004000")')
    parser.add_argument(dest='train', type=str,
                        help='Train number (e.g. "617Я")')
    parser.add_argument(dest='date', type=str,
                        help='Desired date. Follow this pattern: 05.05.2019')
    parser.add_argument('--type', dest='car_type', choices=['Плац', 'Люкс', 'Купе'], default='Плац',
                        help='Defines car type. default=\'Плац\'')
    parser.add_argument('--count', dest='count', type=int, default=1,
                        help='Quantity of tickets. Default is 1')

    args = parser.parse_args()

    rzd_args = {
        'bEntire': 'false',
        'code0': args.departure,
        'code1': args.destination,
        'dir': '0',
        'dt0': args.date,
        'tnum0': args.train,
    }

    pprint(rzd_args)

    mon = AsyncMonitor(rzd_args, args.count, args.car_type, delay_base=-5)
    asyncio.run(mon.run())


if __name__ == '__main__':
    main()
