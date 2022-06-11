import asyncio
import datetime
import itertools
import logging
import random
import traceback

from app.configs import monitor as config
from rzd_client import client
from rzd_client import models
from rzd_client import common

logger = logging.getLogger(__name__)


class AsyncMonitor:
    def __init__(
            self,
            args,
            requested_count=1,
            cars_type=models.ServiceCategory(1),
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

        self.stop = False
        self.last_message = None
        self.last_time = None

    @staticmethod
    async def default_callback(string):
        logger.info(string)

    def _get_seats_count_in_car(self, car: models.Car):

        if self.mask:
            projected = [i1 and i2 for i1, i2 in zip(self.mask, car.seats)]
            projected.extend(car.seats[len(self.mask):])
        else:
            projected = car.seats

        count = sum(projected)
        if self.same_coupe and self.requested_count > 1:
            if count < self.requested_count:
                return 0
            count = 0
            coupe_part = itertools.islice(projected, config.LAST_COUPE_SEAT)
            for coupe in common.grouper_it(self.coupe_size, coupe_part):
                coupe_seats = sum(coupe)
                if coupe_seats >= self.requested_count:
                    count += coupe_seats
        return count

    def _count_tickets_filtered(self, train: models.TrainDetailed) -> int:
        total = sum(
            self._get_seats_count_in_car(car)
            for car in train.cars
            if car.category.code == self.cars_type.code
        )
        return total

    async def run(self):
        first_request = True
        async with client.RZDClient() as client_:
            while not self.stop:
                try:
                    train = await client_.fetch_train_detailed(args=self.args)
                    tickets = self._count_tickets_filtered(train)
                    msg = f'Total: {tickets} tickets'
                    self.last_message = msg
                    self.last_time = datetime.datetime.now()
                    logger.info(f'{self.log_prefix}{msg}')
                    if tickets >= self.requested_count:
                        await self.callback(msg)
                        if first_request:
                            return
                        await asyncio.sleep(120 + self.delay_base * random.random())
                    first_request = False
                except common.RZDNegativeResponse:
                    raise
                except Exception:
                    logger.warning(traceback.format_exc())
                finally:
                    await asyncio.sleep(5 + self.delay_base * random.random())
