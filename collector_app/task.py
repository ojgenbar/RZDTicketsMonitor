import asyncio
import dataclasses
import logging
import typing

from sqlalchemy.orm import Session

from collector_app import orm
from collector_app import worker_queue
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
        return not self._stop

    async def callback(self, trains: typing.List[models.TrainOverview]):
        logger.info(f'ID: {self._id}. Fetched {len(trains)} trains.')
        await self._write_statistics(trains)
        await asyncio.sleep(10)
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
