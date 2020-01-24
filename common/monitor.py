import asyncio
import datetime
import logging
import random
import traceback
from pprint import pformat

import aiohttp

from common import config


class RZDNegativeResponse(RuntimeError):
    pass


class AsyncMonitor:
    def __init__(
            self,
            args,
            requested_count=1,
            cars_type='Плац',
            *,
            delay_base=config.BASIC_DELAY_BASE,
            callback=None,
            prefix='',
    ):
        self.args = args
        self.requested_count = requested_count
        self.cars_type = cars_type
        self.delay_base = delay_base
        self.callback = callback or self.default_callback
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
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
        data = data['lst'][0]
        if data['result'] != 'OK':
            raise RZDNegativeResponse(data['error'])
        cars = data['cars']
        filtered_cars = [c for c in cars if c['type'] == self.cars_type]
        return filtered_cars

    @staticmethod
    def get_places_count(cars):
        return sum(c['seats'][0]['free'] for c in cars)

    async def make_request(self, result_json):
        url = config.BASE_URL

        async with self.session.post(
                url, data=result_json, headers=self.headers,
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
        if data['result'] == 'RID':
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