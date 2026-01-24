from django.core.management.base import BaseCommand
from projects.models import \
    Project  # <--- 'your_app_name' ni o'z ilovangiz nomiga o'zgartiring (masalan: core yoki main)
from projects.views import run_security_scan
import time


class Command(BaseCommand):
    help = 'Barcha tekshirilmagan loyihalarni skanerlash'

    def handle(self, *args, **kwargs):
        # Hali tekshirilmagan (is_scanned=False) va kodi bor loyihalarni olamiz
        projects = Project.objects.filter(is_scanned=False).exclude(source_code='')

        count = projects.count()
        self.stdout.write(self.style.WARNING(f"Jami {count} ta loyiha tekshirilmoqda..."))

        for project in projects:
            self.stdout.write(f"Scanning: {project.title} (ID: {project.id})...")

            # Tekshiruv funksiyasini chaqiramiz
            run_security_scan(project.id)

            # Serverni qiynamaslik uchun har biridan keyin 2 soniya kutamiz
            time.sleep(2)

        self.stdout.write(self.style.SUCCESS("Barcha loyihalar tekshirib bo'lindi!"))