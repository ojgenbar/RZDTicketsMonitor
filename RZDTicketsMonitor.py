import traceback

import requests
from urllib.parse import urlencode
from pprint import pprint
import time
import json
import copy
import random
from datetime import datetime


BASE_URL_PATTERN = r'https://pass.rzd.ru/timetable/public/en?layer_id=5764'


class Monitor:
    def __init__(self, args, requested_count=1, cars_type="Плац"):
        self.args = args
        self.requested_count = requested_count
        self.cars_type = cars_type
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0',
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

    def get_cars(self, data):
        cars = data["lst"][0]["cars"]
        plaz = [c for c in cars if c['type'] == self.cars_type]
        return plaz

    @staticmethod
    def get_places_count(cars):
        return sum(c["seats"][0]["free"] for c in cars)

    @staticmethod
    def create_sound():
        for i in range(3):
            print('\a', end='', flush=True)
            time.sleep(0.5)

    def get_data(self):
        args = copy.copy(self.args)

        url = BASE_URL_PATTERN

        session = requests.Session()
        r = session.post(url, data=urlencode(args), headers=self.headers)
        data = r.json()
        rid = str(data['RID'])

        time.sleep(1)
        args['rid'] = rid

        r = session.post(url, data=urlencode(args), headers=self.headers)
        data = r.json()
        # with open('out.json', 'w', encoding='utf8') as f:
        #     json.dump(data, f, indent=4, ensure_ascii=False)
        return data

    def run(self):
        while True:
            try:
                data = self.get_data()
                cars = self.get_cars(data)
                places = self.get_places_count(cars)
                t = datetime.now().strftime('%H:%M:%S')
                print('{}\tTotal: {} tickets'.format(t, places))
                if places >= self.requested_count:
                    self.create_sound()
            except Exception:
                traceback.print_exc()
            finally:
                time.sleep(5 + 10*random.random())


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
    print(args)

    rzd_args = {
        'bEntire': 'false',
        'code0': args.departure,
        'code1': args.destination,
        'dir': '0',
        'dt0': args.date,
        'tnum0': args.train,
    }

    pprint(rzd_args)
    print()

    m = Monitor(rzd_args, args.count, args.car_type)
    m.run()


if __name__ == '__main__':
    main()
