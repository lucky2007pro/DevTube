import logging
from aiogram import Bot, Dispatcher, executor, types

API_TOKEN = 'SIZNING_TOKENINGIZ'

# Loglarni yoqish
logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """
    Foydalanuvchi /start bosganda javob beradi
    """
    await message.reply("Assalomu alaykum! Men DevTube botiman.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)