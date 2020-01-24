from aiogram.dispatcher.filters.state import State, StatesGroup


class MonitorParameters(StatesGroup):
    departure = State()
    destination = State()
    train = State()
    date = State()
    car_type = State()
    count = State()
    ran = State()
