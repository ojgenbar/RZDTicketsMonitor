from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from .configs import bot as config
from .configs import messages
from . import routes

if not config.API_TOKEN:
    msg = messages.SPECIFY_TOKEN_TEMPLATE.format(
        config.API_TOKEN_ENV,
    )
    raise RuntimeError(msg)

bot = Bot(token=config.API_TOKEN, proxy=config.PROXY_URL)

storage = MemoryStorage()
dispatcher = Dispatcher(bot, storage=storage)
messengers = {}

routes.apply_routes(dispatcher)
