from bot_app import dp
from bot_app import forms
from bot_app import handlers

# Main
dp.register_message_handler(handlers.cmd_help, state='*', commands=['help'])
dp.register_message_handler(handlers.cmd_status, state='*', commands=['status'])
dp.register_message_handler(handlers.cmd_start, state='*', commands=['start'])
dp.register_message_handler(handlers.cancel_handler, state='*', commands=['cancel'])

# State dependant
dp.register_message_handler(handlers.process_departure, state=forms.MonitorParameters.departure)
dp.register_message_handler(handlers.process_destination, state=forms.MonitorParameters.destination)
dp.register_message_handler(handlers.process_train, state=forms.MonitorParameters.train)
dp.register_message_handler(handlers.process_date, state=forms.MonitorParameters.date)
dp.register_message_handler(handlers.process_car_type, state=forms.MonitorParameters.car_type)
dp.register_message_handler(handlers.process_count, state=forms.MonitorParameters.count)

# Fails
dp.register_message_handler(handlers.unexpected_text, state='*')
