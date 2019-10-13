import asyncio
import datetime
import json
import logging
import os
import traceback

import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ParseMode

import async_monitor
import config

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


@dp.message_handler(commands='help')
async def cmd_help(message: types.Message):
    msg = config.HELP_STRING
    await message.reply(msg, reply_markup=DEFAULT_MARKUP)


@dp.message_handler(state='*', commands='status')
async def cmd_status(message: types.Message, state: FSMContext):
    if state.user in messengers and not messengers[state.user].stop:
        messanger = messengers[state.user]
        seconds = (datetime.datetime.now() - messanger.last_time).total_seconds()
        last_message = md.text(
            f'Last attempt:',
            md.bold(f'{seconds:.1f}'),
            f'seconds ago. {messanger.last_message}'
        )
        msg = md.text(
            md.text("Status: RZD Monitor is", md.bold("active"), "."),
            md.text("Params:"),
            md.code(f"{dump_to_json(messanger.args)}"),
            last_message,
            sep='\n'
        )
    else:
        msg = md.text(
            md.text("Status: RZD Monitor is "),
            md.bold("down"),
            md.bold("."),
            sep=''
        )
    await message.reply(
        msg,
        reply_markup=DEFAULT_MARKUP,
        parse_mode=ParseMode.MARKDOWN
    )


@dp.message_handler(state='*', commands='start')
async def cmd_start(message: types.Message, state: FSMContext):
    """
    Conversation's entry point
    """
    if state.user in messengers and not messengers[state.user].stop:
        msg = 'Another monitor is ran. Cancel it first: /cancel'
        await message.reply(msg, reply_markup=DEFAULT_MARKUP)
        return

    # Set state
    await Form.departure.set()
    msg = config.HELP_STRING
    await bot.send_message(state.user, msg)
    msg = (
        'What is departure station ID (e.g. "2010290")?\n\n'
        'Some suggestions:\n'
        'ЧЕРЕПОВЕЦ 1: 2010290\n'
        'МОСКВА (ВСЕ ВОКЗАЛЫ): 2000000\n'
        'САНКТ-ПЕТЕРБУРГ (ВСЕ ВОКЗАЛЫ): 2004000\n'
    )
    await message.reply(msg, reply_markup=DIRECTIONS_MARKUP)


# You can use state '*' if you need to handle all states
@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        await message.reply('Nothing to cancel.', reply_markup=DEFAULT_MARKUP)
        return

    logging.info('Cancelling state %r', current_state)
    async with state.proxy():
        messenger = messengers.pop(state.user, None)
        if messenger:
            messenger.stop = True
            await asyncio.sleep(1)
            await messenger.run()

    await state.finish()
    await message.reply('Cancelled.', reply_markup=DEFAULT_MARKUP)


@dp.message_handler(state=Form.departure)
async def process_departure(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['departure'] = prepare_text_input(message.text)

    await Form.next()
    msg = 'What is destination station ID (e.g. "2004000")?'
    await message.reply(msg, reply_markup=DIRECTIONS_MARKUP)


@dp.message_handler(state=Form.destination)
async def process_destination(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['destination'] = prepare_text_input(message.text)

    await Form.next()
    msg = (
        'What is train number (e.g. "617Я")?\n\n'
        'Some suggestions:\n'
        'ВОЛОГДА -- САНКТ-ПЕТЕРБУРГ: 617Я\n'
        'САНКТ-ПЕТЕРБУРГ -- ВОЛОГДА: 618Я\n'
        'МОСКВА -- ЧЕРЕПОВЕЦ: 126Я\n'
        'ЧЕРЕПОВЕЦ -- МОСКВА: 126Ч\n'
    )
    markup = build_suggest_train_markup(data)
    await message.reply(msg, reply_markup=markup)


@dp.message_handler(state=Form.train)
async def process_train(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['train'] = prepare_text_input(message.text)

    await Form.next()
    days = nearest_days_string()
    text = f'What is desired date? Follow this pattern: {days[0]}'
    markup = build_markup_from_list(days)
    await message.reply(text, reply_markup=markup)


@dp.message_handler(state=Form.date)
async def process_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['date'] = prepare_text_input(message.text)

    await Form.next()
    markup = build_markup_from_list(config.SUGGEST_TYPES)
    await message.reply('What car type would you like?', reply_markup=markup)


@dp.message_handler(state=Form.car_type)
async def process_car_type(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['car_type'] = message.text

    markup = build_markup_from_list(config.SUGGEST_COUNT)
    await Form.next()
    await message.reply('Quantity of tickets?', reply_markup=markup)


@dp.message_handler(state=Form.count)
async def process_count(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['count'] = message.text

    await message.reply('Starting...', reply_markup=DEFAULT_MARKUP)
    await start(message, state)


async def start(message, state):
    async def send_message(msg, **kwargs):
        await bot.send_message(message.chat.id, msg, **kwargs)

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

    prefix = f'@{message.from_user.username} {message.from_user.id} '

    mon = async_monitor.AsyncMonitor(
        rzd_args,
        count,
        car_type,
        delay_base=10,
        callback=send_message,
        prefix=prefix
    )
    messengers[state.user] = mon

    msg = md.text(
        md.code(f'{dump_to_json(rzd_args)}'),
        md.text(f'Count: {count}, car type: {car_type}'),
        sep='\n'
    )
    logging.info(f'{prefix}{msg}')
    await send_message(msg, parse_mode=ParseMode.MARKDOWN)
    try:
        await mon.run()
    except async_monitor.RZDNegativeResponse as e:
        msg = (
            f'Failed to start Monitor:\n'
            f'RZD response message: "{str(e)}"'
        )
        await send_message(msg)
        messengers.pop(state.user, None)


@dp.message_handler()
async def unexpected_text(message: types.Message):
    msg = 'Unexpected text. Type /help for documentation.'
    await message.reply(msg)


def dump_to_json(data):
    return json.dumps(data, indent=4, ensure_ascii=False)


def prepare_text_input(text):
    if text[0] == '/':
        text = text[1:]
    return text


def nearest_days_string(length=3):
    date = datetime.datetime.now().date()

    res = []
    for i in range(length):
        date = date + datetime.timedelta(days=1)
        res.append(date.strftime('%d.%m.%Y'))
    return res


def build_markup_from_list(lst):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add(*lst)
    return markup


def build_suggest_train_markup(data):
    departure = data['departure']
    destination = data['destination']
    trains = config.SUGGEST_TRAINS.get((departure, destination), [])
    return build_markup_from_list(trains) if trains else EMPTY_MARKUP


DEFAULT_MARKUP = build_markup_from_list(config.DEFAULT_MARKUP_BUTTONS)
DIRECTIONS_MARKUP = build_markup_from_list(config.SUGGEST_DIRECTIONS)
EMPTY_MARKUP = types.ReplyKeyboardRemove()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
