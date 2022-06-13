import dataclasses
import datetime
import decimal
import typing

from . import config
from . import common


@dataclasses.dataclass
class Station:
    code: int
    name: typing.Optional[str] = None


@dataclasses.dataclass
class TrainRoute:
    departure_station: Station
    arrival_station: Station

    @classmethod
    def from_rzd_json(cls, data: dict):
        departure_station = Station(
            code=data.get('routeCode0'),
            name=data.get('route0')
        )
        arrival_station = Station(
            code=data.get('routeCode1'),
            name=data.get('route1')
        )

        instance = cls(
            departure_station=departure_station,
            arrival_station=arrival_station,
        )
        return instance


@dataclasses.dataclass
class ServiceCategory:
    code: int

    @property
    def char_code(self):
        return config.CHAR_CODE_BY_SERVICE_CATEGORY_MAPPER.get(self.code, config.UNKNOWN_STR)


@dataclasses.dataclass
class AvailableServiceCategory:
    category: ServiceCategory
    free_seats: int
    price_from: decimal.Decimal
    price_to: typing.Optional[decimal.Decimal]
    rzd_bonus_points: decimal.Decimal

    @classmethod
    def from_rzd_json(cls, data: dict):
        instance = cls(
            category=ServiceCategory(data['typeCarNumCode']),
            free_seats=data['freeSeats'],
            price_from=decimal.Decimal(data['price']),
            price_to=decimal.Decimal(data['priceMax']) if data.get('priceMax') else None,
            rzd_bonus_points=decimal.Decimal(data.get('rzdBonusPoints', 0))
        )
        return instance


@dataclasses.dataclass
class Car:
    category: ServiceCategory
    number: str
    seats: typing.List[bool]
    seats_count: int

    @classmethod
    def from_rzd_data(cls, data):
        seats, count = cls._get_seats_list(data['places'])
        instance = Car(
            category=ServiceCategory(data['ctypei']),
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


@dataclasses.dataclass
class TrainOverview:
    number: str
    brand: typing.Optional[str]
    carrier: typing.Optional[str]
    route: TrainRoute
    service_categories: typing.List[AvailableServiceCategory]
    departure_station: Station
    arrival_station: Station
    departure_datetime: datetime.datetime
    arrival_datetime: datetime.datetime
    time_in_way_string: str

    _raw_data: typing.Optional[dict] = None

    def show_raw_data(self):
        return self._raw_data

    @classmethod
    def from_rzd_json(cls, data):
        departure_station = Station(
            code=data['code0'],
            name=data['station0']
        )
        arrival_station = Station(
            code=data['code1'],
            name=data['station1']
        )
        service_categories = [
            AvailableServiceCategory.from_rzd_json(d)
            for d in data.get('serviceCategories', [])
        ]
        instance = cls(
            number=data['number'],
            brand=data.get('brand'),
            carrier=data.get('carrier'),
            route=TrainRoute.from_rzd_json(data),
            service_categories=service_categories,
            departure_station=departure_station,
            arrival_station=arrival_station,
            departure_datetime=common.parse_rzd_date_time(data['date0'], data['time0']),
            arrival_datetime=common.parse_rzd_date_time(data['date1'], data['time1']),
            time_in_way_string=data.get('timeInWay'),
            _raw_data=data
        )
        return instance


@dataclasses.dataclass
class TrainDetailed:
    number: str
    route: TrainRoute
    departure_station: Station
    arrival_station: Station
    departure_datetime: datetime.datetime
    arrival_datetime: datetime.datetime
    time_in_way_string: str
    cars: typing.List[Car]

    _raw_data: typing.Optional[dict] = None

    @classmethod
    def from_rzd_json(cls, data):
        departure_station = Station(
            code=data['code0'],
            name=data['station0']
        )
        arrival_station = Station(
            code=data['code1'],
            name=data['station1']
        )
        cars = [
            Car.from_rzd_data(raw)
            for raw in data['cars']
        ]
        instance = cls(
            number=data['number'],
            route=TrainRoute.from_rzd_json(data),
            departure_station=departure_station,
            arrival_station=arrival_station,
            departure_datetime=common.parse_rzd_date_time(data['date0'], data['time0']),
            arrival_datetime=common.parse_rzd_date_time(data['date1'], data['time1']),
            time_in_way_string=data.get('timeInWay'),
            cars=cars,
            _raw_data=data
        )
        return instance


@dataclasses.dataclass
class TrainDetailedRequestArgs:
    departure_station: Station
    arrival_station: Station
    departure_date: datetime.date
    train_number: str

    def as_rzd_args(self):
        args = {
            'bEntire': 'false',
            'code0': self.departure_station.code,
            'code1': self.arrival_station.code,
            'dir': '0',
            'dt0': common.format_rzd_date(self.departure_date),
            'tnum0': self.train_number,
        }
        return args

    @classmethod
    def from_rzd_args(cls, args: dict):
        instance = cls(
            departure_station=Station(code=args['code0']),
            arrival_station=Station(code=args['code1']),
            departure_date=common.parse_rzd_date(args['dt0']),
            train_number=args.get('tnum0'),
        )
        return instance


@dataclasses.dataclass
class TrainsOverviewRequestArgs:
    departure_station: Station
    arrival_station: Station
    departure_date: datetime.date

    def as_rzd_args(self):
        args = {
            'dir': '0',
            'tfl': '3',
            'code0': self.departure_station.code,
            'code1': self.arrival_station.code,
            'dt0': common.format_rzd_date(self.departure_date),
            'checkSeats': '0',
            'withoutSeats': 'y',
            'version': '2',
            'actorType': 'desktop_2016',
        }
        return args

    @classmethod
    def from_rzd_args(cls, args: dict):
        instance = cls(
            departure_station=Station(code=args['code0']),
            arrival_station=Station(code=args['code1']),
            departure_date=common.parse_rzd_date(args['dt0']),
        )
        return instance
