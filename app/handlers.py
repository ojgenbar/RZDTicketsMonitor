import asyncio
import datetime
import logging
import traceback

import aiogram.utils.markdown as md
from aiogram import dispatcher
from aiogram import types
from aiogram.types import ParseMode

from app import bot
import functools
import itertools
from app import forms
from app import helpers
from app import markups
from app import suggests, monitor
from app.configs import bot as config
from app.configs import messages


async def cmd_help(message: types.Message):
    msg = messages.HELP_STRING
    await message.reply(msg, reply_markup=markups.DEFAULT_MARKUP)


async def cmd_status(message: types.Message, state: dispatcher.FSMContext):
    if state.user in bot.messengers and not bot.messengers[state.user].stop:
        messanger = bot.messengers[state.user]
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


async def cmd_start(message: types.Message, state: dispatcher.FSMContext):
    """
    Conversation's entry point
    """
    if state.user in bot.messengers and not bot.messengers[state.user].stop:
        msg = messages.ANOTHER_MONITOR_IS_RUN
        await message.reply(msg, reply_markup=markups.DEFAULT_MARKUP)
        return

    # Set state
    await forms.MonitorParameters.date.set()

    days = helpers.nearest_days_string()
    text = messages.QUESTION_DATE_TEMPLATE.format(days[0])
    markup = markups.build_from_list(days)
    await message.reply(text, reply_markup=markup)


async def cmd_cancel(message: types.Message, state: dispatcher.FSMContext):
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
        messenger = bot.messengers.pop(state.user, None)
        if messenger:
            messenger.stop = True
            await asyncio.sleep(1)
            await messenger.run()

    await state.finish()
    await message.reply('Cancelled.', reply_markup=markups.DEFAULT_MARKUP)


async def process_date(message: types.Message, state: dispatcher.FSMContext):
    async with state.proxy() as data:
        string = helpers.prepare_text_input(message.text)
        try:
            string = helpers.validate_date_string(string)
        except ValueError as exc:
            await message.reply(str(exc).capitalize())
            return
        data['date'] = string

    await forms.MonitorParameters.next()
    msg = messages.QUESTION_DEPARTURE_STATION
    await message.reply(msg, reply_markup=markups.DIRECTIONS_MARKUP)


async def process_departure(
        message: types.Message, state: dispatcher.FSMContext,
):
    async with state.proxy() as data:
        string = helpers.prepare_text_input(message.text)
        suggester = suggests.StationSuggester(string)
        await suggester.suggest_station()
        if not suggester.is_exact_match:
            msg = messages.CANNOT_FIND_EXACT_MATCH
            markup = markups.build_from_list(suggester.suggestions.keys())
        else:
            data['departure'] = suggester.match_id
            await forms.MonitorParameters.next()
            msg = messages.QUESTION_DESTINATION_STATION
            markup = markups.DIRECTIONS_MARKUP
    await message.reply(msg, reply_markup=markup)


async def _send_trains(send_func, pre_message, trains):
    if pre_message:
        await send_func(pre_message)
    left = 0
    step = config.MAX_TRAINS_PER_MESSAGE
    values = list(trains.values())
    while left < len(trains):
        right = left + step
        trains_to_send = (
            train.to_message()
            for train in itertools.islice(values, left, right)
        )
        await send_func('\n\n'.join(trains_to_send))
        left += step


async def process_destination(
        message: types.Message, state: dispatcher.FSMContext,
):
    async with state.proxy() as data:
        string = helpers.prepare_text_input(message.text)
        suggester = suggests.StationSuggester(string)
        await suggester.suggest_station()
        if not suggester.is_exact_match:
            msg = messages.CANNOT_FIND_EXACT_MATCH
            markup = markups.build_from_list(suggester.suggestions.keys())
        else:
            await bot.bot.send_message(state.user, messages.WAIT_TRAINS_SEARCH)
            data['destination'] = suggester.match_id
            trains = await suggests.trains(
                data['departure'], data['destination'], data['date'],
            )
            if not trains:
                await bot.bot.send_message(state.user, messages.NO_TRAINS)
                await cmd_cancel(message, state)
                return
            await forms.MonitorParameters.next()
            send_function = functools.partial(
                message.reply, parse_mode=ParseMode.MARKDOWN,
            )
            await _send_trains(
                send_function, messages.AVAILABLE_TRAINS_HEADER, trains,
            )
            msg = messages.CHOOSE_TRAIN_NUMBER_TEMPLATE.format(
                next(iter(trains)),
            )
            markup = markups.build_from_list(
                number for number in sorted(trains)
            )
    await message.reply(
        msg, reply_markup=markup, parse_mode=ParseMode.MARKDOWN,
    )


async def process_train(message: types.Message, state: dispatcher.FSMContext):
    async with state.proxy() as data:
        data['train'] = helpers.prepare_text_input(message.text)

    await forms.MonitorParameters.next()
    markup = markups.build_from_list(config.SUGGEST_TYPES)
    await message.reply(
        messages.QUESTION_CAR_TYPE,
        reply_markup=markup,
        parse_mode=ParseMode.MARKDOWN,
    )


async def process_car_type(
        message: types.Message, state: dispatcher.FSMContext,
):
    async with state.proxy() as data:
        data['car_type'] = message.text

    markup = markups.build_from_list(config.SUGGEST_COUNT)
    await forms.MonitorParameters.next()
    await message.reply(
        messages.QUESTION_TICKETS_QUANTITY, reply_markup=markup,
    )


async def process_count(message: types.Message, state: dispatcher.FSMContext):
    async with state.proxy() as data:
        string = message.text
        try:
            count = helpers.validate_count(string)
        except ValueError as exc:
            await message.reply(str(exc).capitalize())
            return
        data['count'] = count

    await message.reply(messages.STARTING, reply_markup=markups.DEFAULT_MARKUP)
    await start(message, state)


async def start(message, state):
    async def send_message(msg, **kwargs):
        await bot.bot.send_message(message.chat.id, msg, **kwargs)

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
            count = data['count']
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
    bot.messengers[state.user] = mon

    msg = md.text(
        md.code(f'{helpers.dump_to_json(rzd_args)}'),
        md.text(f'Count: {count}, car type: {car_type}'),
        sep='\n',
    )
    logging.info(f'{prefix}{msg}')
    await send_message(msg, parse_mode=ParseMode.MARKDOWN)
    try:
        await mon.run()
        await send_message(
            messages.MONITOR_IS_SHUT_DOWN, parse_mode=ParseMode.MARKDOWN,
        )
    except monitor.RZDNegativeResponse as e:
        msg = messages.FAILED_TO_START_TEMPLATE.format(str(e))
        await send_message(msg)
    bot.messengers.pop(state.user, None)


async def unexpected_text(message: types.Message):
    await message.reply(messages.UNEXPECTED_TEXT)
