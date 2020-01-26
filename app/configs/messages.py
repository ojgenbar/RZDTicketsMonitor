CANNOT_FIND_EXACT_MATCH = (
    "Can't find exact match. "
    "Choose one of below or check spelling and type it correctly."
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

QUESTION_CAR_TYPE = (
    'What car category would you like '
    '(as in the message above: e.g. "*Плац*")?'
)
QUESTION_DEPARTURE_STATION = 'What is departure station ID (e.g. "Санкт-Петербург")?'
QUESTION_DESTINATION_STATION = 'What is destination station ID (e.g. "Москва")?'
WAIT_TRAINS_SEARCH = "I'm looking for available trains, wait..."
NO_TRAINS = 'No trains meet expectations! Cancelling...'
QUESTION_TICKETS_QUANTITY = 'Quantity of tickets?'
STARTING = 'Starting...'
FAILED_TO_START_TEMPLATE = (
    'Failed to start Monitor:\nRZD response message: "{}"'
)

UNEXPECTED_TEXT = 'Unexpected text. Type /help for documentation.'
