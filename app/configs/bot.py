import os

HELP_STRING = (
    'Hi!\n'
    'Wanna buy ticket to train but there are no available? Try this!\n'
    'This is RZD Tickets monitor. Send us data about a train and we will '
    'watch if some tickets appear!\n'
    'Type /start to start\n'
    'Type /cancel to cancel monitor\n'
    'Type /help to show this help\n'
)

SUGGEST_TRAINS = {
    ('ЧЕРЕПОВЕЦ 1', 'МОСКВА'): ['126Ч'],
    ('МОСКВА', 'ЧЕРЕПОВЕЦ 1'): ['126Я'],
    ('ЧЕРЕПОВЕЦ 1', 'САНКТ-ПЕТЕРБУРГ'): ['617Я'],
    ('САНКТ-ПЕТЕРБУРГ', 'ЧЕРЕПОВЕЦ 1'): ['618Я'],
    ('САНКТ-ПЕТЕРБУРГ', 'МОСКВА'): ['118А'],
    ('МОСКВА', 'САНКТ-ПЕТЕРБУРГ'): ['030А'],
}

SUGGEST_TYPES = ['Плац', 'Купе', 'Люкс']

SUGGEST_COUNT = [str(i) for i in range(1, 4)]

SUGGEST_DIRECTIONS = set()
for key in SUGGEST_TRAINS.keys():
    SUGGEST_DIRECTIONS.update(key)
SUGGEST_DIRECTIONS = sorted(SUGGEST_DIRECTIONS)

DEFAULT_MARKUP_BUTTONS = ['/start', '/cancel', '/status']


API_TOKEN_ENV = 'RZD_TICKETS_MONITOR_BOT_TOKEN'
PROXY_URL_ENV = 'RZD_TICKETS_MONITOR_BOT_PROXY'
API_TOKEN = os.getenv(API_TOKEN_ENV)
PROXY_URL = os.getenv(PROXY_URL_ENV)
MAX_TRAINS_PER_MESSAGE = 18

__all__ = [
    'API_TOKEN',
    'API_TOKEN_ENV',
    'HELP_STRING',
    'MAX_TRAINS_PER_MESSAGE',
    'PROXY_URL',
    'PROXY_URL_ENV',
    'SUGGEST_COUNT',
    'SUGGEST_DIRECTIONS',
    'SUGGEST_TRAINS',
    'SUGGEST_TYPES',
]
