import google.generativeai as genai
import time

# SIZNING KALITINGIZ
MY_API_KEY = "AIzaSyBvhtf1WqvoYTEc0uH3Ci3u5seg8oI6zMk"

genai.configure(api_key=MY_API_KEY)

# Sizning ro'yxatingizdagi BARCHA modellar (models/ so'zisiz)
candidates = [
    # --- Yangi 2.0 va 2.5 seriyalar ---
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash-exp",
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-2.0-flash-exp-image-generation",
    "gemini-2.0-flash-lite-001",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash-lite-preview-02-05",
    "gemini-2.0-flash-lite-preview",
    "gemini-exp-1206",

    # --- Gemma va Maxsus modellar ---
    "gemma-3-1b-it",
    "gemma-3-4b-it",
    "gemma-3-12b-it",
    "gemma-3-27b-it",
    "gemma-3n-e4b-it",
    "gemma-3n-e2b-it",

    # --- Eng so'nggi barqaror versiyalar ---
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
    "gemini-pro-latest",

    # --- Kelajak versiyalari (Preview) ---
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash-image",
    "gemini-2.5-flash-preview-09-2025",
    "gemini-2.5-flash-lite-preview-09-2025",
    "gemini-3-pro-preview",
    "gemini-3-flash-preview",
    "gemini-3-pro-image-preview",
    "nano-banana-pro-preview",
    "gemini-robotics-er-1.5-preview",
    "gemini-2.5-computer-use-preview-10-2025",
    "deep-research-pro-preview-12-2025",

    # --- Eski ishonchli variantlar ---
    "gemini-1.5-flash",
    "gemini-1.5-pro"
]

print(f"🔍 Jami {len(candidates)} ta model tekshirilmoqda...\n")
print("-" * 60)
print(f"{'MODEL NOMI':<45} | {'NATIJA'}")
print("-" * 60)

working_models = []

for model_name in candidates:
    try:
        model = genai.GenerativeModel(model_name)
        # Kichik so'rov yuboramiz
        response = model.generate_content("Test", request_options={"timeout": 5})

        print(f"{model_name:<45} | ✅ ISHLADI! (Bepul)")
        working_models.append(model_name)

    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            print(f"{model_name:<45} | ❌ Limit (Pullik/Quota)")
        elif "404" in error_msg:
            print(f"{model_name:<45} | ❌ Topilmadi (404)")
        elif "503" in error_msg:
            print(f"{model_name:<45} | ⚠️ Server band")
        else:
            # Ba'zi modellar matn emas, rasm so'rashi mumkin
            print(f"{model_name:<45} | ⚠️ Boshqa xato")

    # Google serverini qiynamaslik uchun 1 soniya kutamiz
    time.sleep(1)

print("-" * 60)
print("\n🏆 TAVSIYA QILINGAN MODELLAR (Shulardan birini tanlang):")
for m in working_models:
    print(f"🚀 {m}")