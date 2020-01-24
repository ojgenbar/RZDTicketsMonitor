import asyncio
import datetime
import logging
import traceback

import aiogram.utils.markdown as md
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import ParseMode

from bot_app import bot
from bot_app import config
from bot_app import forms
from bot_app import helpers
from bot_app import markups
from bot_app import messengers
from bot_app import monitor


async def cmd_help(message: types.Message):
    msg = config.HELP_STRING
    await message.reply(msg, reply_markup=markups.DEFAULT_MARKUP)


async def cmd_status(message: types.Message, state: FSMContext):
    if state.user in messengers and not messengers[state.user].stop:
        messanger = messengers[state.user]
        if messanger.last_time:
            seconds = (
                datetime.datetime.now() - messanger.last_time
            ).total_seconds()
            last_message = md.text(
                f'Last attempt:',
                md.bold(f'{seconds:.1f}'),
                f'seconds ago. {messanger.last_message}',
            )
        else:
            last_message = ''
        msg = md.text(
            md.text('Status: RZD Monitor is', md.bold('active'), '.'),
            md.text('Params:'),
            md.code(f'{helpers.dump_to_json(messanger.args)}'),
            last_message,
            sep='\n',
        )
    else:
        msg = md.text(
            md.text('Status: RZD Monitor is '),
            md.bold('down'),
            md.bold('.'),
            sep='',
        )
    await message.reply(
        msg,
        reply_markup=markups.DEFAULT_MARKUP,
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_start(message: types.Message, state: FSMContext):
    """
    Conversation's entry point
    """
    if state.user in messengers and not messengers[state.user].stop:
        msg = 'Another monitor is ran. Cancel it first: /cancel'
        await message.reply(msg, reply_markup=markups.DEFAULT_MARKUP)
        return

    # Set state
    await forms.MonitorParameters.departure.set()
    msg = config.HELP_STRING
    await bot.send_message(state.user, msg)
    msg = (
        'What is departure station ID (e.g. "2010290")?\n\n'
        'Some suggestions:\n'
        'ЧЕРЕПОВЕЦ 1: 2010290\n'
        'МОСКВА (ВСЕ ВОКЗАЛЫ): 2000000\n'
        'САНКТ-ПЕТЕРБУРГ (ВСЕ ВОКЗАЛЫ): 2004000\n'
    )
    await message.reply(msg, reply_markup=markups.DIRECTIONS_MARKUP)


async def cancel_handler(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        await message.reply(
            'Nothing to cancel.', reply_markup=markups.DEFAULT_MARKUP,
        )
        return

    logging.info('Cancelling state %r', current_state)
    async with state.proxy():
        messenger = messengers.pop(state.user, None)
        if messenger:
            messenger.stop = True
            await asyncio.sleep(1)
            await messenger.run()

    await state.finish()
    await message.reply('Cancelled.', reply_markup=markups.DEFAULT_MARKUP)


async def process_departure(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['departure'] = helpers.prepare_text_input(message.text)

    await forms.MonitorParameters.next()
    msg = 'What is destination station ID (e.g. "2004000")?'
    await message.reply(msg, reply_markup=markups.DIRECTIONS_MARKUP)


async def process_destination(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['destination'] = helpers.prepare_text_input(message.text)

    await forms.MonitorParameters.next()
    msg = (
        'What is train number (e.g. "617Я")?\n\n'
        'Some suggestions:\n'
        'ВОЛОГДА -- САНКТ-ПЕТЕРБУРГ: 617Я\n'
        'САНКТ-ПЕТЕРБУРГ -- ВОЛОГДА: 618Я\n'
        'МОСКВА -- ЧЕРЕПОВЕЦ: 126Я\n'
        'ЧЕРЕПОВЕЦ -- МОСКВА: 126Ч\n'
    )
    markup = markups.build_suggest_train_markup(data)
    await message.reply(msg, reply_markup=markup)


async def process_train(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['train'] = helpers.prepare_text_input(message.text)

    await forms.MonitorParameters.next()
    days = helpers.nearest_days_string()
    text = f'What is desired date? Follow this pattern: {days[0]}'
    markup = markups.build_markup_from_list(days)
    await message.reply(text, reply_markup=markup)


async def process_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['date'] = helpers.prepare_text_input(message.text)

    await forms.MonitorParameters.next()
    markup = markups.build_markup_from_list(config.SUGGEST_TYPES)
    await message.reply('What car type would you like?', reply_markup=markup)


async def process_car_type(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['car_type'] = message.text

    markup = markups.build_markup_from_list(config.SUGGEST_COUNT)
    await forms.MonitorParameters.next()
    await message.reply('Quantity of tickets?', reply_markup=markup)


async def process_count(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['count'] = message.text

    await message.reply('Starting...', reply_markup=markups.DEFAULT_MARKUP)
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

    mon = monitor.AsyncMonitor(
        rzd_args,
        count,
        car_type,
        delay_base=10,
        callback=send_message,
        prefix=prefix,
    )
    messengers[state.user] = mon

    msg = md.text(
        md.code(f'{helpers.dump_to_json(rzd_args)}'),
        md.text(f'Count: {count}, car type: {car_type}'),
        sep='\n',
    )
    logging.info(f'{prefix}{msg}')
    await send_message(msg, parse_mode=ParseMode.MARKDOWN)
    try:
        await mon.run()
    except monitor.RZDNegativeResponse as e:
        msg = f'Failed to start Monitor:\n' f'RZD response message: "{str(e)}"'
        await send_message(msg)
        messengers.pop(state.user, None)


async def unexpected_text(message: types.Message):
    msg = 'Unexpected text. Type /help for documentation.'
    await message.reply(msg)
