# projects/management/commands/release_funds.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from projects.models import Transaction
from django.db import transaction

class Command(BaseCommand):
    help = 'Muddati kelgan muzlatilgan pullarni avtomatik sotuvchilarga o\'tkazadi'

    def handle(self, *args, **options):
        now = timezone.now()
        # Vaqti kelgan, statusi 'hold' bo'lgan tranzaksiyalar
        expired_trxs = Transaction.objects.filter(
            status=Transaction.HOLD,
            release_at__lte=now
        )

        count = 0
        for trx in expired_trxs:
            try:
                with transaction.atomic():
                    seller_profile = trx.project.author.profile
                    # Faqat muzlatilgan balansda pul bo'lsagina ishlaydi
                    if seller_profile.frozen_balance >= trx.amount:
                        seller_profile.frozen_balance -= trx.amount
                        seller_profile.balance += trx.amount
                        seller_profile.save()

                        trx.status = Transaction.COMPLETED
                        trx.save()
                        count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Xato #{trx.id}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Muvaffaqiyatli: {count} ta pul o'tkazildi."))