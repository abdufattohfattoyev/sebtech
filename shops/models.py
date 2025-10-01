from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum


class Shop(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Do'kon nomi")
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'userprofile__role': 'boss'},
        verbose_name="Do'kon egasi"
    )
    created_at = models.DateField(default=timezone.now, verbose_name="Yaratilgan sana")

    class Meta:
        verbose_name = "Do'kon"
        verbose_name_plural = "Do'konlar"

    def __str__(self):
        return self.name


class Customer(models.Model):
    name = models.CharField(max_length=100, verbose_name="Mijoz ismi")
    phone_number = models.CharField(
        max_length=15,
        unique=True,  # YANGI: telefon raqam unique
        verbose_name="Telefon raqami"
    )
    image = models.ImageField(upload_to='customers/', blank=True, null=True, verbose_name="Mijoz rasmi")
    notes = models.TextField(null=True, blank=True, verbose_name="Izohlar")
    created_at = models.DateField(default=timezone.now, verbose_name="Qo'shilgan sana")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Qo'shgan foydalanuvchi"
    )

    class Meta:
        verbose_name = "Mijoz"
        verbose_name_plural = "Mijozlar"

    def __str__(self):
        return f"{self.name} - {self.phone_number}"

    @property
    def total_debt(self):
        """Mijozning umumiy qarzini hisoblash"""
        from sales.models import Debt
        active_debts = Debt.objects.filter(
            customer=self,
            status='active'
        ).aggregate(
            total_debt=Sum('debt_amount'),
            total_paid=Sum('paid_amount')
        )
        total_debt = active_debts['total_debt'] or 0
        total_paid = active_debts['total_paid'] or 0
        return max(0, total_debt - total_paid)

    @property
    def total_purchases(self):
        """Mijozning umumiy xaridlarini hisoblash"""
        from sales.models import PhoneSale, AccessorySale, PhoneExchange
        phone_sales = self.phone_sales.aggregate(total=Sum('sale_price'))['total'] or 0
        accessory_sales = self.accessory_sales.aggregate(total=Sum('total_price'))['total'] or 0
        phone_exchanges = self.phone_exchanges.aggregate(total=Sum('new_phone_price'))['total'] or 0
        return phone_sales + accessory_sales + phone_exchanges

    @property
    def active_debts_count(self):
        """Faol qarzlar soni"""
        from sales.models import Debt
        return Debt.objects.filter(customer=self, status='active').count()

    @property
    def total_paid_amount(self):
        """Umumiy to'langan summa"""
        from sales.models import Debt
        return Debt.objects.filter(customer=self).aggregate(total=Sum('paid_amount'))['total'] or 0

    def get_purchase_history(self):
        """Xarid tarixi — payment_method olib tashlandi"""
        from sales.models import PhoneSale, AccessorySale, PhoneExchange
        purchases = []
        for sale in self.phone_sales.select_related('phone').order_by('-sale_date'):
            purchases.append({
                'type': 'phone_sale',
                'date': sale.sale_date,
                'item': str(sale.phone),
                'amount': sale.sale_price,
                'object': sale
            })
        for sale in self.accessory_sales.select_related('accessory').order_by('-sale_date'):
            purchases.append({
                'type': 'accessory_sale',
                'date': sale.sale_date,
                'item': f"{sale.accessory.name} x{sale.quantity}",
                'amount': sale.total_price,
                'object': sale
            })
        for exchange in self.phone_exchanges.select_related('new_phone').order_by('-exchange_date'):
            purchases.append({
                'type': 'phone_exchange',
                'date': exchange.exchange_date,
                'item': f"{exchange.old_phone_model} → {exchange.new_phone}",
                'amount': exchange.new_phone_price,
                'object': exchange
            })
        purchases.sort(key=lambda x: x['date'], reverse=True)
        return purchases

    def get_debt_history(self):
        """Qarz tarixi"""
        from sales.models import Debt
        return self.debts.select_related('creditor').order_by('-created_at')
