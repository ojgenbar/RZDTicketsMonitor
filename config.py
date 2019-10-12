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

__all__ = [
    'HELP_STRING', 'SUGGEST_COUNT', 'SUGGEST_DIRECTIONS', 'SUGGEST_TRAINS',
    'SUGGEST_TYPES'
]
DEFAULT_MARKUP_BUTTONS = ['/start', '/cancel', '/status']