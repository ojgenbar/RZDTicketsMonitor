from app import bot
from aiogram import executor


def main():
    executor.start_polling(
        bot.dispatcher,
        skip_updates=True,
        on_startup=bot.on_startup,
        on_shutdown=bot.on_shutdown,
    )


if __name__ == '__main__':
    main()
