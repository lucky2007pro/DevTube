#!/usr/bin/env bash
set -e

echo "=== 1. Paketlar o'rnatilmoqda ==="
pip install -r requirements.txt

echo "=== 2. sites migration tarixga qo'shilmoqda ==="
python manage.py shell -c "
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute(\"SELECT COUNT(*) FROM django_migrations WHERE app='sites' AND name='0001_initial'\")
    exists = cursor.fetchone()[0]
    if not exists:
        cursor.execute(\"INSERT INTO django_migrations (app, name, applied) VALUES ('sites', '0001_initial', NOW())\")
        print('sites 0001_initial yozuvi qoshildi')
    else:
        print('sites 0001_initial allaqachon mavjud')
"

echo "=== 3. Migratsiyalar bajarilmoqda ==="
python manage.py migrate --fake-initial

echo "=== 4. Static fayllar yig'ilmoqda ==="
python manage.py collectstatic --no-input

echo "=== Deploy muvaffaqiyatli! ==="