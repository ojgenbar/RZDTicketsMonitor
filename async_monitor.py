import asyncio
import datetime
import logging
import random
import traceback
from pprint import pprint

import aiohttp

BASE_URL = r'https://pass.rzd.ru/timetable/public/en?layer_id=5764'

logging.basicConfig(level=logging.INFO)


class AsyncMonitor:
    def __init__(self, args, requested_count=1, cars_type="Плац", *,
                 delay_base=10, callback=None):
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

    @staticmethod
    async def default_callback(string):
        logging.info(string)

    def get_cars(self, data):
        cars = data["lst"][0]["cars"]
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
        return result_json

    async def get_data(self):
        args = {**self.args}
        rid_data = await self.make_request(args)
        rid = str(rid_data['RID'])
        args['rid'] = rid

        await asyncio.sleep(1)

        data = await self.make_request(args)
        return data

    async def run(self):
        async with aiohttp.ClientSession() as self.session:
            while not self.stop:
                try:
                    data = await self.get_data()
                    cars = self.get_cars(data)
                    places = self.get_places_count(cars)
                    t = datetime.datetime.now().strftime('%H:%M:%S')
                    msg = f'{t}\tTotal: {places} tickets'
                    logging.info(msg)
                    if places >= self.requested_count:
                        await self.callback(msg)
                except Exception:
                    logging.warning(traceback.format_exc())
                finally:
                    await asyncio.sleep(5 + self.delay_base * random.random())


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
