#!/usr/bin/env bash
set -e

echo "=== 1. Paketlar o'rnatilmoqda ==="
pip install -r requirements.txt

echo "=== 2. Eski yolg'on sites yozuvlari o'chirilmoqda ==="
python manage.py shell -c "
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute(\"DELETE FROM django_migrations WHERE app='sites'\")
    print('sites migration yozuvlari tozalandi')
"

echo "=== 3. Sites jadvali HAQIQATAN yaratilmoqda ==="
python manage.py migrate sites

echo "=== 4. Barcha migratsiyalar bajarilmoqda ==="
python manage.py migrate

echo "=== 5. Static fayllar yig'ilmoqda ==="
python manage.py collectstatic --no-input

echo "=== Deploy muvaffaqiyatli! ==="