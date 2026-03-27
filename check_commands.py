
import os
import sys

try:
    import django
    from django.conf import settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    print("Django setup successful")
    
    from django.core.management import get_commands
    commands = get_commands()
    if 'collectstatic' in commands:
        print("collectstatic command found")
    else:
        print("collectstatic command NOT found")
        print("Available commands:", list(commands.keys()))

except Exception as e:
    import traceback
    print("Error during Django setup:")
    traceback.print_exc()
    sys.exit(1)
