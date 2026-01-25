import os
import requests
# DIQQAT: Bu yangi kutubxona importi (google-generativeai EMAS)
from google import genai
from django.conf import settings

# ==========================================
# API KEYLARNI TIZIMDAN OLISH
# ==========================================
# Render Environment yoki settings.py dan oladi
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or getattr(settings, 'GEMINI_API_KEY', None)
VT_API_KEY = os.environ.get("VT_API_KEY") or getattr(settings, 'VT_API_KEY', None)


def scan_with_gemini(code_content):
    """
    Kod mantiqini Gemini 2.0 orqali tekshirish (Yangi SDK).
    """
    if not GEMINI_API_KEY:
        print("DEBUG: Gemini API Key topilmadi.")
        return "SAFE: Tahlil qilinmadi (API kalit yo'q)"

    try:
        # --- YANGI SINTAKSIS BOSHLANDI ---
        # 1. Client yaratamiz
        client = genai.Client(api_key=GEMINI_API_KEY)

        prompt = f"""
        Sen kiberxavfsizlik ekspertisan. Quyidagi dastur kodini tahlil qil.

        Agar kodda quyidagilar bo'lsa "DANGER" deb javob ber:
        - Virus yoki troyan
        - Tizim fayllarini o'chirish (os.remove, rm -rf)
        - Parol o'g'irlash yoki keylogger
        - Orqa eshik (Backdoor) yoki teskari ulanish (Reverse shell)

        Agar kod xavfsiz bo'lsa "SAFE" deb javob ber.
        Javobingda faqat xulosa va qisqa izoh (o'zbek tilida) bo'lsin.

        KOD:
        {code_content[:8000]}  # Limitni oshirdik
        """

        # 2. So'rov yuboramiz (model nomi o'zgargan bo'lishi mumkin)
        response = client.models.generate_content(
            model='gemini-2.0-flash',  # Yoki 'gemini-1.5-flash'
            contents=prompt
        )

        # 3. Javobni qaytaramiz
        if response.text:
            return response.text
        return "SAFE: AI javob bermadi."

    except Exception as e:
        print(f"Gemini Xatosi: {e}")
        return f"SAFE: AI Xatosi ({str(e)})"


def scan_with_virustotal(file_url, file_name):
    """
    Faylni Cloudinary URL orqali yuklab olib, VirusTotalga yuborish.
    """
    if not VT_API_KEY:
        return None, "VirusTotal API Key topilmadi"

    vt_url = "https://www.virustotal.com/api/v3/files"
    headers = {"x-apikey": VT_API_KEY}

    try:
        # 1. Faylni Cloudinarydan vaqtincha xotiraga yuklab olish
        print(f"VirusTotal uchun fayl yuklanmoqda: {file_url}")
        file_response = requests.get(file_url, timeout=30)  # Timeout qo'shildi

        if file_response.status_code != 200:
            return None, "Faylni serverdan yuklab bo'lmadi"

        file_content = file_response.content

        # 2. Faylni VirusTotalga yuborish
        files = {"file": (file_name, file_content)}
        response = requests.post(vt_url, headers=headers, files=files)

        if response.status_code == 200:
            json_resp = response.json()
            # Hisobot ID sini olamiz
            file_id = json_resp['data']['id']
            # To'g'ridan-to'g'ri hisobot havolasini qaytaramiz
            return f"https://www.virustotal.com/gui/file/{file_id}", "success"
        else:
            print(f"VT Error: {response.text}")
            return None, f"VT Xatosi: {response.status_code}"

    except Exception as e:
        print(f"VT Exception: {e}")
        return None, str(e)