from django.db import migrations
from django.contrib.postgres.operations import TrigramExtension

class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0001_initial'), # Yoki oxirgi migratsiya raqami
    ]

    operations = [
        TrigramExtension(),
    ]