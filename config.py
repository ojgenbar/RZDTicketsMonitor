import os
import logging.handlers

SLEEP_AFTER_RID_REQUEST = 1
BASIC_DELAY_BASE = 20

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
    ('2010290', '2000000'): ['126Ч'],
    ('2000000', '2010290'): ['126Я'],
    ('2010290', '2004000'): ['617Я'],
    ('2004000', '2010290'): ['618Я'],
    ('2004000', '2000000'): ['118А'],
    ('2000000', '2004000'): ['030А'],
}

SUGGEST_TYPES = ["Плац", "Купе", "Люкс"]

SUGGEST_COUNT = [str(i) for i in range(1, 4)]

SUGGEST_DIRECTIONS = set()
for key in SUGGEST_TRAINS.keys():
    SUGGEST_DIRECTIONS.update(key)
SUGGEST_DIRECTIONS = sorted(SUGGEST_DIRECTIONS)

DEFAULT_MARKUP_BUTTONS = ['/start', '/cancel', '/status']


LOG_FILENAME = 'logs/rzd_monitor.log'
os.makedirs(os.path.dirname(os.path.abspath(LOG_FILENAME)), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-5.5s]  %(message)s",
    handlers=[
        logging.handlers.RotatingFileHandler(
            LOG_FILENAME, 'a', encoding='utf8', maxBytes=100*2**20, backupCount=5
        ),
        logging.StreamHandler()
    ])


__all__ = [
    'HELP_STRING', 'SUGGEST_COUNT', 'SUGGEST_DIRECTIONS', 'SUGGEST_TRAINS',
    'SUGGEST_TYPES'
]
