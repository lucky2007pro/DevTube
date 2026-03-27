
import os
import django
from django.core.management import get_commands

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

commands = get_commands()
if 'collectstatic' in commands:
    print("collectstatic command found")
else:
    print("collectstatic command NOT found")
    print("Available commands:", list(commands.keys()))
