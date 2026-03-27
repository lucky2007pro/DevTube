import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.sites.models import Site
from django.contrib.auth.models import User

def setup():
    # 1. SITE_ID xatosini (500) yo'qotish uchun
    site, created = Site.objects.get_or_create(id=1)
    site.domain = 'https://devtube-6nkr.onrender.com'
    site.name = 'DevTube'
    site.save()
    print("Site ID=1 muvaffaqiyatli yaratildi!")

    # 2. Superuser (Admin) yaratish (Shell'ga kirmaslik uchun)
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'usa2000302@gmail.com', 'Hojiakbar2007')
        print("Admin yaratildi: admin / Hojiakbar2007")

if __name__ == "__main__":
    setup()