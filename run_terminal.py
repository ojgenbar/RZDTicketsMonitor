import asyncio
from pprint import pprint

from app.monitor import AsyncMonitor


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='RZD monitor. Monitors if desired tickets are available.',
    )
    parser.add_argument(
        dest='departure',
        type=str,
        help='Departure station ID (e.g. "2010290")',
    )
    parser.add_argument(
        dest='destination',
        type=str,
        help='Destination station ID (e.g. "2004000")',
    )
    parser.add_argument(
        dest='train', type=str, help='Train number (e.g. "617Я")',
    )
    parser.add_argument(
        dest='date',
        type=str,
        help='Desired date. Follow this pattern: 05.05.2019',
    )
    parser.add_argument(
        '--type',
        dest='car_type',
        choices=['Плац', 'Люкс', 'Купе', 'Сид', 'Мягкий'],
        default='Плац',
        help='Defines car type. default=\'Плац\'',
    )
    parser.add_argument(
        '--count',
        dest='count',
        type=int,
        default=1,
        help='Quantity of tickets. Default is 1',
    )

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

    mon = AsyncMonitor(rzd_args, args.count, args.car_type)
    asyncio.run(mon.run())


if __name__ == '__main__':
    main()
