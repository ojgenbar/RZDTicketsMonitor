from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from .configs import bot as config

if not config.API_TOKEN:
    msg = 'You must specify bot token ' 'in env variable "{}"!'.format(
        config.API_TOKEN_ENV,
    )
    raise RuntimeError(msg)

bot = Bot(token=config.API_TOKEN, proxy=config.PROXY_URL)

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

messengers = {}

from . import routes
