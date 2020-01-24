import bot_app
from bot_app import forms
from bot_app import handlers

_register = bot_app.dp.register_message_handler

# Main
_register(handlers.cmd_help, state='*', commands=['help'])
_register(handlers.cmd_status, state='*', commands=['status'])
_register(handlers.cmd_start, state='*', commands=['start'])
_register(handlers.cancel_handler, state='*', commands=['cancel'])

# State dependant
_parameters = forms.MonitorParameters
_register(handlers.process_departure, state=_parameters.departure)
_register(handlers.process_destination, state=_parameters.destination)
_register(handlers.process_train, state=_parameters.train)
_register(handlers.process_date, state=_parameters.date)
_register(handlers.process_car_type, state=_parameters.car_type)
_register(handlers.process_count, state=_parameters.count)

# Fails
_register(handlers.unexpected_text, state='*')