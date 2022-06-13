import asyncio
import collections
import logging
import random
import time
import typing

from collector_app.configs import collector as config
from rzd_client import client
from rzd_client import models

logger = logging.getLogger(__name__)


class WorkerQueue:
    _client: client.RZDClient

    def __init__(self):
        self._request_queue = collections.deque()
        self._tasks_queue = asyncio.Queue()

    @staticmethod
    def _generate_delay():
        return random.uniform(*config.SLEEP_AFTER_REQUEST_RANGE)

    async def schedule_query(self, args: models.TrainsOverviewRequestArgs, callback: typing.Callable):
        if len(self._request_queue) >= config.MAX_QUEUE_SIZE:
            logger.warning(f'Queue exceeded max size! Current size: {len(self._request_queue)}.')
        while len(self._request_queue) >= config.MAX_QUEUE_SIZE:
            await asyncio.sleep(config.MAX_QUEUE_SIZE)
        self._request_queue.append((args, callback, time.time()))

    async def _process_one_task(self):
        args, callback, start = self._request_queue.popleft()
        try:
            trains = await self._client.fetch_trains_overview(args)
        except Exception:
            logger.exception('Cannot fetch Trains. Stop for now.')
            return
        logger.info('Successfully fetched trains. Spent in queue: %s sec.', time.time() - start)
        self._tasks_queue.put_nowait(asyncio.create_task(callback(trains)))

    async def _tasks_worker(self):
        while True:
            task = await self._tasks_queue.get()
            await task
            self._tasks_queue.task_done()

    async def run(self):
        asyncio.create_task(self._tasks_worker())
        async with client.RZDClient() as self._client:
            while True:
                if self._request_queue:
                    await self._process_one_task()
                await asyncio.sleep(config.SLEEP_FOR_QUEUE)
