import requests

# BotFather bergan token
TELEGRAM_BOT_TOKEN = "8259030267:AAHxrF49K5oloAryc-Vi-ig8xDBBnwuMKEg"


def send_telegram_message(chat_id, message):
    """
    Foydalanuvchining Telegramiga xabar yuborish funksiyasi.
    """
    if not chat_id:
        return  # Agar ID bo'lmasa, hech narsa qilmaymiz

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"  # Chiroyli yozuvlar (qalin, kursiv) uchun
    }

    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Telegramga yuborishda xato: {e}")