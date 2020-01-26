import asyncio
import datetime
import logging
import random
import traceback
from pprint import pformat

import aiohttp

from app import helpers
from app.configs import rzd as config
from app.configs import messages


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
        self.headers = config.HEADERS
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

    async def get_data(self):
        data = await rzd_rid_request(
            self.session, config.BASE_URL, self.args, headers=self.headers
        )
        return data

    async def run(self):
        first_request = True
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
                        if first_request:
                            return
                    first_request = False
                except RZDNegativeResponse:
                    raise
                except Exception:
                    logging.warning(traceback.format_exc())
                finally:
                    await asyncio.sleep(5 + self.delay_base * random.random())


async def rzd_request(session, url, args, *, headers=None):
    if not headers:
        headers = config.HEADERS
    log_extra = {
        'args_': args,
        'url': url
    }
    logging.info('request: {!r}'.format(log_extra))
    async with session.post(
            url, data=args, headers=headers,
    ) as resp:
        result_json = await resp.json(content_type=None)
        logging.info(helpers.prepare_to_log(pformat(result_json)))
    return result_json


async def rzd_rid_request(
        session, url, args, *,
        headers=None
):
    args_copy = args.copy()
    rid_data = await rzd_request(session, url, args_copy, headers=headers)
    if rid_data['result'] == 'OK':
        return rid_data

    rid = str(rid_data['RID'])

    args_copy['rid'] = rid

    rid_sleep = config.SLEEP_AFTER_RID_REQUEST
    await asyncio.sleep(rid_sleep)

    for i in range(5):
        data = await rzd_request(session, url, args_copy, headers=headers)
        result = data['result']
        if result == 'RID':
            logging.warning(
                f'Unexpected RID result. Data: {repr(data)}'
            )
            await asyncio.sleep(rid_sleep)
        elif result == 'OK':
            return data
        elif result == 'FAIL':
            break

    raise RuntimeError(messages.CANNOT_FETCH_RESULT_FROM_RZD)