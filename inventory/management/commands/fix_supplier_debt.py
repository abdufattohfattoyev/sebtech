from django.core.management.base import BaseCommand
from inventory.models import Phone, Supplier
from decimal import Decimal


class Command(BaseCommand):
    help = 'Taminotchilar qarzini tuzatish'

    def handle(self, *args, **options):
        # 1. Noto'g'ri telefonlarni tuzatish
        broken_phones = Phone.objects.filter(
            source_type='supplier',
            payment_status='paid',
            paid_amount=Decimal('0')
        )

        count = broken_phones.count()
        self.stdout.write(f"Topildi: {count} ta noto'g'ri telefon")

        for phone in broken_phones:
            phone.paid_amount = phone.cost_price
            phone.save()

        self.stdout.write(self.style.SUCCESS(f'✓ {count} ta telefon tuzatildi'))

        # 2. Barcha taminotchilarni yangilash
        suppliers = Supplier.objects.all()
        for supplier in suppliers:
            result = supplier.recalculate_debt_and_payments()
            self.stdout.write(
                f"{supplier.name}: Qarz=${result['total_debt']}, "
                f"To'langan=${result['total_paid']}"
            )

        self.stdout.write(self.style.SUCCESS('✓ Barcha taminotchilar yangilandi!'))