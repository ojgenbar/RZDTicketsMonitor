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

routes.apply_routes(dispatcher)


async def on_startup(_):
    global rzd_client
    rzd_client = client.RZDClient()
    await rzd_client.__aenter__()


async def on_shutdown(_):
    global rzd_client
    if rzd_client:
        await rzd_client.__aexit__(None, None, None)
