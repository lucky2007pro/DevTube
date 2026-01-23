import os
import django

# Django sozlamalarini yuklaymiz
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def create_admin():
    username = "admin"           # Login
    password = "12345678"        # Parol (Keyin o'zgartirib olasiz)
    email = "admin@example.com"

    # Agar admin avval yaratilmagan bo'lsa, yaratamiz
    if not User.objects.filter(username=username).exists():
        print(f"Superuser yaratilmoqda: {username}...")
        User.objects.create_superuser(username, email, password)
        print("Muvaffaqiyatli yaratildi!")
    else:
        print("Superuser allaqachon mavjud. Yaratish shart emas.")

if __name__ == "__main__":
    create_admin()