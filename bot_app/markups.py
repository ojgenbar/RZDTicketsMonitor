from aiogram import types

from bot_app import config


def build_markup_from_list(lst):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add(*lst)
    return markup


def build_suggest_train_markup(data):
    departure = data['departure']
    destination = data['destination']
    trains = config.SUGGEST_TRAINS.get((departure, destination), [])
    return build_markup_from_list(trains) if trains else EMPTY_MARKUP


DEFAULT_MARKUP = build_markup_from_list(config.DEFAULT_MARKUP_BUTTONS)
DIRECTIONS_MARKUP = build_markup_from_list(config.SUGGEST_DIRECTIONS)
EMPTY_MARKUP = types.ReplyKeyboardRemove()
