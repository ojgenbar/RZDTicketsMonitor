from aiogram.dispatcher.filters import state


class MonitorParameters(state.StatesGroup):
    departure = state.State()
    destination = state.State()
    train = state.State()
    date = state.State()
    car_type = state.State()
    count = state.State()
    ran = state.State()
