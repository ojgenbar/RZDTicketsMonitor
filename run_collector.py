import asyncio

from collector_app import collector
from collector_app import orm


def main():
    orm.create_all()
    asyncio.run(collector.Collector().run())


if __name__ == '__main__':
    main()

