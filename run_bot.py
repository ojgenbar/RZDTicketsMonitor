from bot_app import dp
from aiogram import executor

executor.start_polling(dp, skip_updates=True)
