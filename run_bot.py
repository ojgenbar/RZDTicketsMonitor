from bot_app import dp
from aiogram import executor


def main():
    executor.start_polling(dp, skip_updates=True)


if __name__ == '__main__':
    main()
