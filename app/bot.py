import contextlib

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from app import routes
from app.configs import bot as config
from app.configs import messages
from rzd_client import client

if not config.API_TOKEN:
    msg = messages.SPECIFY_TOKEN_TEMPLATE.format(
        config.API_TOKEN_ENV,
    )
    raise RuntimeError(msg)

bot = Bot(token=config.API_TOKEN, proxy=config.PROXY_URL)

storage = MemoryStorage()
dispatcher = Dispatcher(bot, storage=storage)
messengers = {}
rzd_client: client.RZDClient | None = None
_lifespan: contextlib.AsyncExitStack | None = None

routes.apply_routes(dispatcher)


async def on_startup(_):
    global rzd_client, _lifespan
    _lifespan = contextlib.AsyncExitStack()
    rzd_client = await _lifespan.enter_async_context(client.RZDClient())


async def on_shutdown(_):
    global _lifespan
    if _lifespan:
        await _lifespan.aclose()
        _lifespan = None
