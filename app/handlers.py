import datetime
import datetime
import functools
import itertools
import logging
import traceback

import aiogram.utils.markdown as md
from aiogram import dispatcher
from aiogram import types
from aiogram.types import ParseMode

from app import bot
from app import forms
from app import helpers
from app import markups
from app import monitor
from app import suggests
from app.configs import bot as config
from app.configs import messages
from rzd_client import common
from rzd_client import models

logger = logging.getLogger(__name__)


async def cmd_help(message: types.Message):
    msg = messages.HELP_STRING
    await message.reply(msg, reply_markup=markups.DEFAULT_MARKUP)


async def cmd_status(message: types.Message, state: dispatcher.FSMContext):
    if state.user in bot.messengers and not bot.messengers[state.user].stop:
        messenger = bot.messengers[state.user]
        if messenger.last_time:
            seconds = (
                datetime.datetime.now() - messenger.last_time
            ).total_seconds()
            last_message = md.text(
                f'Last attempt:',
                md.bold(f'{seconds:.1f}'),
                f'seconds ago. {messenger.last_message}',
            )
        else:
            last_message = ''
        msg = md.text(
            md.text('Status: RZD Monitor is', md.bold('active'), '.'),
            md.text('Params:'),
            md.code(f'{helpers.dump_to_json(messenger.args.as_rzd_args())}'),
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


async def cmd_set(message: types.Message, state: dispatcher.FSMContext):
    """
    Setting Monitor entry point
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
            messages.NOTHING_TO_CANCEL, reply_markup=markups.DEFAULT_MARKUP,
        )
        return

    logger.info('Cancelling state %r', current_state)
    async with state.proxy():
        messenger = bot.messengers.get(state.user, None)
        if messenger:
            messenger.stop = True
            text = messages.CANCELLING_MONITOR
        else:
            text = messages.CANCELLED
    await state.finish()
    await message.reply(text, reply_markup=markups.DEFAULT_MARKUP)


async def process_date(message: types.Message, state: dispatcher.FSMContext):
    async with state.proxy() as data:
        string = helpers.prepare_text_input(message.text)
        try:
            date = helpers.parse_date(string)
        except ValueError as exc:
            await message.reply(str(exc).capitalize())
            return
        data['date'] = date

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
            data['departure'] = models.Station(suggester.match_id)
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
            data['destination'] = models.Station(suggester.match_id)
            trains = await suggests.trains(
                models.TrainsOverviewRequestArgs(
                    data['departure'], data['destination'], data['date'],
                )
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
            params = helpers.get_params_from_count(string)
        except ValueError as exc:
            await message.reply(str(exc).capitalize())
            return
        data['count'] = params

    await message.reply(messages.STARTING, reply_markup=markups.DEFAULT_MARKUP)
    await start(message, state)


async def start(message, state):
    async def send_message(msg, **kwargs):
        await bot.bot.send_message(message.chat.id, msg, **kwargs)

    async with state.proxy() as data:
        try:
            rzd_args = models.TrainDetailedRequestArgs(
                data['departure'],
                data['destination'],
                data['date'],
                data['train'],
            )
            params = data['count']
            car_type = helpers.service_category_by_char_code(data['car_type'])
        except Exception:
            traceback.print_exc()
            return

    prefix = f'@{message.from_user.username} {message.from_user.id} '

    mon = monitor.AsyncMonitor(
        args=rzd_args,
        cars_type=car_type,
        callback=send_message,
        prefix=prefix,
        **params,
    )
    bot.messengers[state.user] = mon

    msg = md.text(
        md.code(f'{helpers.dump_to_json(rzd_args.as_rzd_args())}'),
        md.code(f'{helpers.dump_to_json(params)}'),
        md.text(f'Count: {params["requested_count"]}, car type: {car_type.char_code}'),
        sep='\n',
    )
    logger.info(f'{prefix}{msg}')
    await send_message(msg, parse_mode=ParseMode.MARKDOWN)
    await send_message_to_logs(f'{prefix}\n{msg}')
    try:
        await mon.run()
        await send_message(
            messages.MONITOR_IS_SHUT_DOWN, parse_mode=ParseMode.MARKDOWN,
        )
    except common.RZDNegativeResponse as e:
        msg = messages.FAILED_TO_START_TEMPLATE.format(str(e))
        await send_message(msg)

    await state.finish()
    bot.messengers.pop(state.user, None)
    await send_message(messages.CANCELLED, reply_markup=markups.DEFAULT_MARKUP)
    await send_message_to_logs(f'{prefix}\n{messages.CANCELLED}')


async def unexpected_text(message: types.Message):
    await message.reply(messages.UNEXPECTED_TEXT)


async def send_message_to_logs(*args, **kwargs):
    if not config.LOGS_CHANNEL:
        return
    await bot.bot.send_message(config.LOGS_CHANNEL, *args, **kwargs)
