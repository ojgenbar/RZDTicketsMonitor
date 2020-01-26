from app import bot
from aiogram import executor


def main():
    executor.start_polling(bot.dp, skip_updates=True)


if __name__ == '__main__':
    main()
