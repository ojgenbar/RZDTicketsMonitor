import os


SUGGEST_DIRECTIONS = ['МОСКВА', 'САНКТ-ПЕТЕРБУРГ', 'ЧЕРЕПОВЕЦ 1']
SUGGEST_TYPES = ['Плац', 'Купе', 'Сид']
SUGGEST_COUNT = [str(i) for i in range(1, 4)]

DEFAULT_MARKUP_BUTTONS = ['/set', '/cancel', '/status']

API_TOKEN_ENV = 'RZD_TICKETS_MONITOR_BOT_TOKEN'
PROXY_URL_ENV = 'RZD_TICKETS_MONITOR_BOT_PROXY'
API_TOKEN = os.getenv(API_TOKEN_ENV)
PROXY_URL = os.getenv(PROXY_URL_ENV)
MAX_TRAINS_PER_MESSAGE = 15

COMMAND_SYMBOL = '@'

__all__ = [
    'API_TOKEN',
    'API_TOKEN_ENV',
    'MAX_TRAINS_PER_MESSAGE',
    'PROXY_URL',
    'PROXY_URL_ENV',
    'SUGGEST_COUNT',
    'SUGGEST_DIRECTIONS',
    'SUGGEST_TYPES',
]
