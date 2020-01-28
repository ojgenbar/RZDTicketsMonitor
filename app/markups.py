from aiogram import types

from app.configs import bot as config


def build_from_list(iterable):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add(*iterable)
    return markup


DEFAULT_MARKUP = build_from_list(config.DEFAULT_MARKUP_BUTTONS)
DIRECTIONS_MARKUP = build_from_list(config.SUGGEST_DIRECTIONS)
EMPTY_MARKUP = types.ReplyKeyboardRemove()
