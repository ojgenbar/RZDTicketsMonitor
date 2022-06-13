import asyncio
import dataclasses
import datetime
import logging
import typing

import pytz
from sqlalchemy.orm import Session

from collector_app import orm
from collector_app import worker_queue
from collector_app.configs import collector as config
from rzd_client import models

logger = logging.getLogger(__name__)


class Task:
    def __init__(
            self,
            args: models.TrainsOverviewRequestArgs,
            config: orm.Config,
            worker: worker_queue.WorkerQueue
    ):
        self._args = args
        self._config = config
        self._worker = worker

        self._id = config.id
        self._stop = False

    def _check_can_process(self) -> bool:
        today = today_msk()
        if today > self._args.departure_date:
            logger.info(f'ID: {self._id}. Departure date at past. Stop.')
            return False
        return not self._stop

    def _calculate_delay(self) -> int:
        days = (self._args.departure_date - today_msk()).days
        days = max(days, 0)
        delay = calculate_delay(days)
        logger.info(f'ID: {self._id}. Delay: {delay} sec.')
        return delay

    async def callback(self, is_success: bool, trains: typing.List[models.TrainOverview]):
        if not is_success:
            logger.warning(f'ID: {self._id}. Cannot fetch trains. Schedule next.')
            await self.schedule_next()
            return
        logger.info(f'ID: {self._id}. Fetched {len(trains)} trains.')
        await self._write_statistics(trains)
        await asyncio.sleep(self._calculate_delay())
        await self.schedule_next()

    def stop(self):
        self._stop = True

    async def _write_statistics(self, trains):
        data_objs, data_raw_obj = extract_statistics(trains, self._config)
        with Session(orm.engine) as session:
            session.add_all([data_raw_obj, *data_objs])
            session.commit()

    async def schedule_next(self):
        if not self._check_can_process():
            logger.info(f'Task stopped, id: {self._id}')
            return
        await self._worker.schedule_query(self._args, self.callback)


def _tickets_from_service_categories(
        service_categories: typing.List[models.AvailableServiceCategory]
) -> typing.List[dict]:
    res = []
    for category in service_categories:
        data = dataclasses.asdict(category)
        data['category']['char_code'] = category.category.char_code
        data['price_from'] = str(category.price_from)
        data['price_to'] = str(category.price_to) if category.price_to else None
        data['rzd_bonus_points'] = str(category.rzd_bonus_points) if category.rzd_bonus_points else None
        res.append(data)
    return res


def extract_statistics(trains: typing.List[models.TrainOverview], config):
    data_objs = []
    raw_data = []
    for train in trains:
        data_objs.append(
            orm.CollectedData(
                train_number=train.number,
                tickets_json=_tickets_from_service_categories(train.service_categories),
                config=config,
            )
        )
        raw_data.append(train.show_raw_data())
    data_raw_obj = orm.CollectedDataRaw(raw_data=raw_data, config=config)
    return data_objs, data_raw_obj


def today_msk():
    return datetime.datetime.now(pytz.timezone('Europe/Moscow')).date()


def calculate_delay(d):
    return min(config.MAX_DELAY_FOR_DATE, 10 + d**2)
