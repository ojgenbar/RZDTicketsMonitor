import asyncio
import dataclasses
import datetime
import itertools
import logging
import random
import traceback
import typing
from pprint import pformat

import aiohttp

from app import helpers
from app.configs import messages
from app.configs import rzd as config


@dataclasses.dataclass
class Car:
    car_type: str
    number: str
    seats: typing.List[bool]
    seats_count: int

    @classmethod
    def from_rzd_data(cls, data):
        seats, count = cls._get_seats_list(data['places'])
        instance = Car(
            car_type=data['type'],
            number=data['cnumber'],
            seats=seats,
            seats_count=count,
        )
        return instance

    @staticmethod
    def _convert_seat_to_int(seat: str):
        if seat.isdigit():
            return int(seat)
        first3 = seat[:3]
        if first3.isdigit():
            return int(first3)
        raise ValueError(f'Cannot convert to int seat string {seat!r}')

    @classmethod
    def _unwrap_seats_range(cls, seats_range):
        left, right = seats_range.split(config.STRING_RANGE_SEP)
        res = range(
            cls._convert_seat_to_int(left),
            cls._convert_seat_to_int(right) + 1
        )
        return res

    @classmethod
    def _get_seats_list(cls, places_string):
        places_set = set()
        for string in places_string.split(config.STRING_LIST_SEP):
            if config.STRING_RANGE_SEP in string:
                places_set.update(cls._unwrap_seats_range(string))
            else:
                places_set.add(cls._convert_seat_to_int(string))

        lst = [False] * max(places_set)
        for seat in places_set:
            lst[seat - 1] = True
        return lst, len(places_set)

    def get_seats_count(self, seats_count=1, mask=None, same_coupe=False, coupe_size=4):
        if mask:
            projected = [i1 and i2 for i1, i2 in zip(mask, self.seats)]
            projected.extend(self.seats[len(mask):])
        else:
            projected = self.seats

        count = sum(projected)
        if same_coupe and seats_count > 1:
            if count < seats_count:
                return 0
            assert coupe_size >= seats_count, messages.SEATS_COUNT_GT_COUPE_SIZE
            count = 0
            coupe_part = itertools.islice(projected, config.LAST_COUPE_SEAT)
            for coupe in helpers.grouper_it(coupe_size, coupe_part):
                coupe_seats = sum(coupe)
                if coupe_seats >= seats_count:
                    count += coupe_seats
        return count


class Train:
    def __init__(self, data):
        self._data = data
        self.cars = self.parse_cars(data)

    @staticmethod
    def parse_cars(data):
        cars = {}
        for car_data in data['lst'][0]['cars']:
            car = Car.from_rzd_data(car_data)
            cars[car.number] = car
        return cars

    def get_seats_count(self, car_type, seats_count=1, mask=None, same_coupe=False, coupe_size=4):
        count = 0
        for car in self.cars.values():
            if car_type != car.car_type:
                continue
            count += car.get_seats_count(seats_count, mask, same_coupe, coupe_size)
        return count


class RZDNegativeResponse(RuntimeError):
    pass


class AsyncMonitor:
    def __init__(
            self,
            args,
            requested_count=1,
            cars_type='Плац',
            mask=None,
            same_coupe=False,
            coupe_size=4,
            *,
            delay_base=config.BASIC_DELAY_BASE,
            callback=None,
            prefix='',
    ):
        self.args = args
        self.requested_count = requested_count
        self.cars_type = cars_type
        self.mask = mask
        self.same_coupe = same_coupe
        self.coupe_size = coupe_size
        self.delay_base = delay_base
        self.callback = callback or self.default_callback
        self.log_prefix = prefix

        self.headers = config.HEADERS
        self.session = None
        self.stop = False
        self.last_message = None
        self.last_time = None

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
            self.session, config.BASE_URL, self.args, headers=self.headers,
        )
        return data

    async def run(self):
        first_request = True
        async with aiohttp.ClientSession() as self.session:
            while not self.stop:
                try:
                    data = await self.get_data()
                    train = Train(data)
                    places = train.get_seats_count(
                        self.cars_type,
                        self.requested_count,
                        self.mask,
                        self.same_coupe,
                        self.coupe_size
                    )
                    msg = f'Total: {places} tickets'
                    self.last_message = msg
                    self.last_time = datetime.datetime.now()
                    logging.info(f'{self.log_prefix}{msg}')
                    if places >= self.requested_count:
                        await self.callback(msg)
                        if first_request:
                            return
                        await asyncio.sleep(120 + self.delay_base * random.random())
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
    log_extra = {'args_': args, 'url': url}
    logging.info('request: {!r}'.format(log_extra))
    async with session.post(url, data=args, headers=headers) as resp:
        result_json = await resp.json(content_type=None)
        logging.info(helpers.prepare_to_log(pformat(result_json)))
    return result_json


async def rzd_rid_request(session, url, args, *, headers=None):
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
            logging.warning(f'Unexpected RID result. Data: {repr(data)}')
            await asyncio.sleep(rid_sleep)
        elif result == 'OK':
            return data
        elif result == 'FAIL':
            break

    raise RuntimeError(messages.CANNOT_FETCH_RESULT_FROM_RZD)
