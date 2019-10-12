import json
import logging
import os
import traceback

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup

from async_monitor import AsyncMonitor

logging.basicConfig(level=logging.INFO)


API_TOKEN = os.getenv('RZD_TICKETS_MONITOR_BOT_TOKEN')
PROXY_URL = os.getenv('RZD_TICKETS_MONITOR_BOT_PROXY')

bot = Bot(token=API_TOKEN, proxy=PROXY_URL)

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class Form(StatesGroup):
    departure = State()
    destination = State()
    train = State()
    date = State()
    car_type = State()
    count = State()
    ran = State()


messengers = {}
HELP_STRING = (
        'Hi!\n'
        'Wanna buy ticket to train but there are no available? Try this!\n'
        'This is RZD Tickets monitor. Send us data about a train and we will '
        'watch if some tickets appear!\n'
        'Type /start to start\n'
        'Type /cancel to cancel monitor\n'
        'Type /help to show this help\n'
    )


@dp.message_handler(commands='help')
async def cmd_help(message: types.Message):
    msg = HELP_STRING
    await message.reply(msg)


@dp.message_handler(state='*', commands='start')
async def cmd_start(message: types.Message, state: FSMContext):
    """
    Conversation's entry point
    """
    # Set state
    await Form.departure.set()
    msg = HELP_STRING
    await bot.send_message(state.user, msg)
    await message.reply('What is departure station ID (e.g. "2010290")?')


# You can use state '*' if you need to handle all states
@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info('Cancelling state %r', current_state)
    async with state.proxy():
        messenger = messengers.pop(state.user, None)
        if messenger:
            messenger.stop = True
            await messenger.run()

    await state.finish()
    await message.reply('Cancelled.', reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(state=Form.departure)
async def process_departure(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['departure'] = message.text

    await Form.next()
    await message.reply('What is destination station ID (e.g. "2004000")?')


@dp.message_handler(state=Form.destination)
async def process_destination(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['destination'] = message.text

    await Form.next()
    await message.reply('What is train number (e.g. "617Я")?')


@dp.message_handler(state=Form.train)
async def process_train(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['train'] = message.text

    await Form.next()
    await message.reply('What is desired date? Follow this pattern: 05.05.2019.')


@dp.message_handler(state=Form.date)
async def process_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['date'] = message.text

    await Form.next()
    await message.reply('What car type would you like? Choose one of: [\'Плац\', \'Люкс\', \'Купе\']')


@dp.message_handler(state=Form.car_type)
async def process_car_type(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['car_type'] = message.text

    await Form.next()
    await message.reply('Quantity of tickets?')


@dp.message_handler(state=Form.count)
async def process_count(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['count'] = message.text
    await start(message, state)


async def start(message, state):
    async def send_message(msg):
        await bot.send_message(message.chat.id, msg)

    await send_message('Starting...')

    async with state.proxy() as data:
        try:
            rzd_args = {
                'bEntire': 'false',
                'code0': data['departure'],
                'code1': data['destination'],
                'dir': '0',
                'dt0': data['date'],
                'tnum0': data['train'],
            }
            count = int(data['count'])
            car_type = data['car_type']
        except Exception:
            traceback.print_exc()
            return

    mon = AsyncMonitor(
        rzd_args,
        count,
        car_type,
        delay_base=-5,
        callback=send_message
    )
    messengers[state.user] = mon

    await send_message(dump_to_json(rzd_args))
    await send_message(f'Count: {count}, car type: {car_type}')
    await mon.run()


@dp.message_handler()
async def unexpected_text(message: types.Message):
    msg = 'Unexpected text. Type /help for documentation.'
    await message.reply(msg)


def dump_to_json(data):
    return json.dumps(data, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
