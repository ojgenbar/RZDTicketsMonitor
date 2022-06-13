import asyncio

from collector_app import collector


def main():
    asyncio.run(collector.Collector().run())


if __name__ == '__main__':
    main()

