import asyncio
import datetime
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from collector_app import orm
from collector_app import worker_queue
from collector_app import task
from collector_app.configs import collector as config
from rzd_client import models

logger = logging.getLogger(__name__)


class Collector:
    _active_tasks: dict
    _worker: worker_queue.WorkerQueue

    async def _fetch_configs_from_db(self):
        with Session(orm.engine) as session:
            all_configs = session.query(orm.Config).all()
        for conf in all_configs:
            if not conf.enabled and conf.id in self._active_tasks:
                self._active_tasks.pop(conf.id)[1].stop()
                continue
            if conf.enabled and conf.id not in self._active_tasks:
                args = models.TrainsOverviewRequestArgs(
                    departure_date=conf.departure_date,
                    departure_station=models.Station(conf.departure_station_id),
                    arrival_station=models.Station(conf.arrival_station_id),
                )
                t = task.Task(args, worker=self._worker, config=conf)
                await t.schedule_next()
                self._active_tasks[conf.id] = (conf, t)

    async def _sync_tasks_from_db(self):
        while True:
            await self._fetch_configs_from_db()
            logger.info('Successfully synced configs')
            await asyncio.sleep(config.SLEEP_CONFIG_FETCH)

    async def _start_worker_loop(self):
        await self._worker.run()

    async def run(self):
        logger.info('Starting collector process.')
        self._worker = worker_queue.WorkerQueue()
        self._active_tasks = {}
        await asyncio.gather(self._sync_tasks_from_db(), self._start_worker_loop())
        logger.info('Stopped collector process.')


def main():
    asyncio.run(Collector().run())


if __name__ == '__main__':
    main()
