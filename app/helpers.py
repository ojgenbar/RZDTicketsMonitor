import datetime
import json


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
