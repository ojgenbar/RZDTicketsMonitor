import os

# Monitor
BASE_URL = r'https://pass.rzd.ru/timetable/public/en?layer_id=5764'
SLEEP_AFTER_RID_REQUEST = 1
SLEEP_AFTER_UNSUCCESSFUL_REQUEST = 3
REQUEST_ATTEMPTS = 10
BASIC_DELAY_BASE = 20
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
}
SOCKS5_PROXY_STRING = os.getenv('SOCKS5_PROXY_STRING')

# Suggest station
MIN_SUGGESTS_SIMILARITY = 70
SUGGESTS_LIMIT = 5
SUGGESTS_BASE_URL = r'http://www.rzd.ru/suggester'

# Suggest train
SUGGEST_TRAINS_URL = r'https://pass.rzd.ru/timetable/public/ru?layer_id=5827'

# Dates
DATE_FORMAT = '%d.%m.%Y'
TIME_FORMAT = '%H:%M'
DATETIME_PARSE_FORMAT = f'{DATE_FORMAT} {TIME_FORMAT}'
DATES_INTERVAL = 121

# Train
STRING_RANGE_SEP = '-'
STRING_LIST_SEP = ','
LAST_COUPE_SEAT = 36

CANNOT_FETCH_RESULT_FROM_RZD = 'Cannot fetch result from RZD site.'

LOGGER_NAME = 'rzd_client'


CHAR_CODE_BY_SERVICE_CATEGORY_MAPPER = {
    1: 'Плац',
    3: 'Сид',
    4: 'Купе',
    5: 'Мягкий',
    6: 'Люкс',
}
UNKNOWN_STR = 'Unknown'
