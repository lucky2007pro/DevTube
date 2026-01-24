import os
import requests
import google.generativeai as genai
from django.conf import settings

# ==========================================
# API KEYLARNI TIZIMDAN OLISH (RENDER UCHUN)
# ==========================================
# Render "Environment Variables" bo'limiga kiritgan kalitlarni o'qiydi
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
VT_API_KEY = os.environ.get("VT_API_KEY")

# Agar kalit bor bo'lsa, Geminini sozlaymiz
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def scan_with_gemini(code_content):
    """
    Kod mantiqini Gemini orqali tekshirish.
    Matn (string) qabul qiladi.
    """
    if not GEMINI_API_KEY:
        return "Gemini API Key topilmadi!"

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        Sen kiberxavfsizlik ekspertisan. Quyidagi kodni tekshir.
        Agar kodda virus, parol o'g'irlash, fayllarni o'chirish yoki zararli amallar bo'lsa "DANGER" deb boshla.
        Agar kod toza bo'lsa "SAFE" deb boshla.
        Qisqa izoh ber (o'zbek tilida).

        KOD:
        {code_content[:4000]}  # 4000 belgigacha tekshiramiz
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Xatosi: {e}"


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
        file_response = requests.get(file_url)

        if file_response.status_code != 200:
            return None, "Faylni Cloudinarydan yuklab bo'lmadi"

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
            return None, f"VT Xatosi: {response.status_code} - {response.text}"

    except Exception as e:
        return None, str(e)