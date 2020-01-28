from app import bot
from aiogram import executor


def main():
    executor.start_polling(bot.dispatcher, skip_updates=True)


if __name__ == '__main__':
    main()
