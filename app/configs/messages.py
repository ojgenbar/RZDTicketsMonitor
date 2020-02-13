SPECIFY_TOKEN_TEMPLATE = 'You must specify bot token in env variable "{}"!'
CANNOT_FIND_EXACT_MATCH = (
    'Can\'t find exact match. '
    'Choose one of the following or check spelling and type it correctly.'
)
AVAILABLE_TRAINS_HEADER = 'Available trains:'

CHOOSE_TRAIN_NUMBER_TEMPLATE = 'Choose train number (e.g. "{}").'

AVAILABLE_TRAINS_TEMPLATE = (
    '*{train.number}* {train.brand}\n'
    '_{train.train_route}_\n'
    '*{train.time_departure}* - *{train.time_arrival}* '
    '({train.time_in_way} in way)\n'
    'Allowed categories: {train.service_categories_string}'
)

QUESTION_DATE_TEMPLATE = 'What is the desired date? Follow this pattern: {}'
QUESTION_CAR_TYPE = (
    'What car category would you like '
    '(as in the message above: e.g. "*Плац*")?'
)
QUESTION_DEPARTURE_STATION = (
    'What is the departure station (e.g. "Санкт-Петербург")?'
)
QUESTION_DESTINATION_STATION = (
    'What is the destination station (e.g. "Москва")?'
)
WAIT_TRAINS_SEARCH = 'I\'m looking for available trains, wait...'
NO_TRAINS = 'No trains meet expectations! Cancelling...'
QUESTION_TICKETS_QUANTITY = 'The number of tickets?'
INVALID_QUANTITY = 'The number must be a positive integer!'
STARTING = 'Starting...'
FAILED_TO_START_TEMPLATE = (
    'Failed to start Monitor:\nRZD response message: "{}"'
)

UNEXPECTED_TEXT = 'Unexpected text. Type /help for documentation.'

DATE_ERROR_TEMPLATE = (
    'Invalid date! The date must be between {} and {}!'
)

ANOTHER_MONITOR_IS_RUN = 'Another monitor is running. Cancel it first: /cancel'
MONITOR_IS_SHUT_DOWN = 'Monitor is shut *down*.'
CANNOT_FETCH_RESULT_FROM_RZD = 'Cannot fetch result from RZD site.'

HELP_STRING = (
    'Hi!\n'
    'Wanna buy a train ticket but there are no available? Try this!\n'
    'This is RZD Tickets monitor. Send us the train details and we will see if '
    'tickets appear!\n\n'
    'Source code:\n'
    'https://github.com/ojgenbar/RZDTicketsMonitor\n\n'
    'Type /set to set new monitor\n'
    'Type /cancel to cancel current monitor\n'
    'Type /help to show this help\n'
)

CANCELLING_MONITOR = "I'm cancelling current monitor, wait..."
NOTHING_TO_CANCEL = 'Nothing to cancel.'
