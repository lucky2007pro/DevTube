from django.db import migrations
from django.contrib.postgres.operations import TrigramExtension

class Migration(migrations.Migration):
    dependencies = [
        # Bu yerda oxirgi migratsiya faylingiz nomi bo'ladi (avtomatik turadi)
    ]

    operations = [
        TrigramExtension(), # <--- Extensionni yoqish buyrug'i
    ]