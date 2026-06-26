import dataclasses
import datetime
import re
import typing

from .. import config
from . import v1 as models_v1


@dataclasses.dataclass
class CarType:
    code: str
    name: str

    @classmethod
    def from_name(cls, name):
        return CAR_TYPE_BY_NAME[name]

    @classmethod
    def from_code(cls, code):
        return CAR_TYPE_BY_CODE[code]


CAR_TYPE_BY_NAME = {}
CAR_TYPE_BY_CODE = {}
for _name, _code in config.CAR_TYPE_CODE_BY_NAME.items():
    _car_type = CarType(_code, _name)
    CAR_TYPE_BY_CODE[_code] = _car_type
    CAR_TYPE_BY_NAME[_name] = _car_type


@dataclasses.dataclass
class Car:
    number: str
    car_type: CarType
    seats: typing.List[bool]

    @staticmethod
    def _convert_seat_to_int(seat: str):
        match = re.search(r'\d+', seat)
        if not match:
            raise ValueError(f'Cannot convert to int seat string {seat!r}')
        return int(match[0])

    @classmethod
    def _parse_seats_string(cls, string: str):
        if not string:
            return []

        places_set = set()
        for string in string.split(config.STRING_LIST_SEP):
            places_set.add(cls._convert_seat_to_int(string))

        lst = [False] * max(places_set)
        for seat in places_set:
            lst[seat - 1] = True
        return lst

    @classmethod
    def from_rzd_data(cls, data: dict):
        car_type = CarType.from_code(code=data['CarType'])

        seats = cls._parse_seats_string(data['FreePlaces'])

        instance = cls(
            number=data['CarNumber'],
            car_type=car_type,
            seats=seats,
        )
        return instance


@dataclasses.dataclass
class TrainDetailed:
    number: str
    cars: typing.List[Car]

    @classmethod
    def from_rzd_data(cls, data: dict):
        instance = cls(
            number=data['TrainInfo']['TrainNumber'],
            cars=cls._parse_cars(data['Cars'])
        )
        return instance

    @staticmethod
    def _merge_cars(car1: Car, car2: Car):
        seats1 = car1.seats
        seats2 = car2.seats
        if len(seats1) < len(seats2):
            seats1, seats2 = seats2, seats1
        for i, val in enumerate(seats2):
            seats1[i] = seats1[i] or val
        car = Car(
            number=car1.number,
            car_type=car1.car_type,
            seats=seats1
        )
        return car

    @classmethod
    def _parse_cars(cls, data: list[dict]):
        cars_dict = {}
        for raw_car in data:
            car = Car.from_rzd_data(raw_car)
            if car.number in cars_dict:
                car = cls._merge_cars(car, cars_dict[car.number])
            cars_dict[car.number] = car
        cars = sorted(cars_dict.values(), key=lambda x: x.number)
        return cars


@dataclasses.dataclass
class TrainDetailedRequestArgs:
    departure_station: models_v1.Station
    arrival_station: models_v1.Station
    departure_date: datetime.date
    train_number: str

    def as_rzd_args(self):
        args = {
            "OriginCode": str(self.departure_station.code),
            "DestinationCode": str(self.arrival_station.code),
            "Provider": "P1",
            "DepartureDate": self.departure_date.isoformat(),
            "TrainNumber": self.train_number,
            "SpecialPlacesDemand": "StandardPlacesAndForDisabledPersons",
            "OnlyFpkBranded": False,
            "CarIssuingType": "All"
        }
        return args

