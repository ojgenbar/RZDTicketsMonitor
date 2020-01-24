from bot_app import dp
from bot_app import handlers
from bot_app import forms

# Main
dp.register_message_handler(handlers.cmd_help, state='*', commands=['help'])
dp.register_message_handler(handlers.cmd_status, state='*', commands=['status'])
dp.register_message_handler(handlers.cmd_start, state='*', commands=['start'])
dp.register_message_handler(handlers.cancel_handler, state='*', commands=['cancel'])

# State dependant
dp.register_message_handler(handlers.process_departure, state=forms.Form.departure)
dp.register_message_handler(handlers.process_destination, state=forms.Form.destination)
dp.register_message_handler(handlers.process_train, state=forms.Form.train)
dp.register_message_handler(handlers.process_date, state=forms.Form.date)
dp.register_message_handler(handlers.process_car_type, state=forms.Form.car_type)
dp.register_message_handler(handlers.process_count, state=forms.Form.count)

# Fails
dp.register_message_handler(handlers.unexpected_text, state='*')
