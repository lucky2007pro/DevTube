#!/usr/bin/env bash
set -e

echo "=== 1. Paketlar o'rnatilmoqda ==="
pip install -r requirements.txt

echo "=== 2. Sites migratsiyasi AVVAL bajarilmoqda ==="
python manage.py migrate sites

echo "=== 3. Barcha migratsiyalar bajarilmoqda ==="
python manage.py migrate

echo "=== 4. Static fayllar yig'ilmoqda ==="
python manage.py collectstatic --no-input

echo "=== Deploy muvaffaqiyatli! ==="