import requests

# BotFather bergan token
TELEGRAM_BOT_TOKEN = "8259030267:AAGz9p2u4tt32yt3eMnpDk67yO2R3vtLXN0"


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

from django.core.signing import TimestampSigner, BadSignature, SignatureExpired

signer = TimestampSigner()

def generate_telegram_link(user):
    """Foydalanuvchi uchun 5 daqiqa amal qiladigan Telegram havolasini yaratadi"""
    # User ID ni shifrlaymiz
    token = signer.sign(user.id)
    # Botingiz username-ini shu yerga yozing (kuchukchasiz)
    bot_username = "DevTubeAlertBot"
    return f"https://t.me/{bot_username}?start={token}"

def verify_telegram_token(token):
    """Tokenni tekshirib, User ID ni qaytaradi"""
    try:
        # Token 300 soniya (5 daqiqa) davomida yaroqli
        user_id = signer.unsign(token, max_age=300)
        return user_id
    except (BadSignature, SignatureExpired):
        return None