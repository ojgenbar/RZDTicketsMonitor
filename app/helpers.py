import argparse
import datetime
import itertools
import json
import logging

from app.configs import messages
from app.configs import rzd as config
from app.configs import bot as bot_config


logger = logging.getLogger(__name__)


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
        date_str = (date + datetime.timedelta(days=i)).strftime('%d.%m.%Y')
        res.append(date_str)
    return res


def prepare_to_log(string):
    return string.replace('\n', '\\n')


def validate_date_string(string):
    string_date = string
    today = datetime.datetime.now().date()
    if 4 <= len(string_date) < 5:
        string_date = '{}.{}'.format(string_date, today.year)
    date_format = config.DATE_FORMAT
    input_date = datetime.datetime.strptime(string_date, date_format).date()
    max_date = today + datetime.timedelta(days=config.DATES_INTERVAL)
    if not today <= input_date <= max_date:
        message = messages.DATE_ERROR_TEMPLATE.format(
            today.strftime(date_format), max_date.strftime(date_format),
        )
        raise ValueError(message)
    return input_date.strftime(date_format)


def get_params_from_count(string):
    split = string.split(bot_config.COMMAND_SYMBOL, 1)
    if len(split) == 2:
        count_str, command_str = split
    else:
        count_str = split[0]
        command_str = None

    count = int(count_str)
    if count < 1:
        raise ValueError(messages.INVALID_QUANTITY)

    params = {'requested_count': count}
    if command_str:
        try:
            params.update(_parse_arguments(command_str))
        except ValueError as exc:
            logger.error(str(exc))
    return params


def _parse_arguments(string=None):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--mask',
        type=lambda s: [bool(int(c)) for c in s],
    )
    parser.add_argument(
        '--same_coupe',
        action='store_true',
    )
    parser.add_argument(
        '--coupe_size',
        type=int,
        default=4
    )
    args, invalid = parser.parse_known_args(string.split())
    if invalid:
        raise ValueError(f'Cannot parse string args: string={string!r}, invalid={invalid!r}')
    return vars(args)


def grouper_it(n, iterable):
    it = iter(iterable)
    while True:
        chunk_it = itertools.islice(it, n)
        try:
            first_el = next(chunk_it)
        except StopIteration:
            return
        yield itertools.chain((first_el,), chunk_it)
