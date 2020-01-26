import datetime
import json
from app.configs import rzd as config
from app.configs import messages


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
            today.strftime(date_format),
            max_date.strftime(date_format)
        )
        raise ValueError(message)
    return input_date.strftime(date_format)
