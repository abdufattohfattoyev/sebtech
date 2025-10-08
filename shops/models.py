from django.core.validators import RegexValidator
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal


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
        unique=True,
        verbose_name="Telefon raqami",
    )
    image = models.ImageField(upload_to='customers/', blank=True, null=True, verbose_name="Mijoz rasmi")
    birth_date = models.DateField(null=True, blank=True, verbose_name="Tug'ilgan kuni")
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
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.phone_number}"

    @property
    def age(self):
        """Mijozning yoshini hisoblash"""
        if self.birth_date:
            today = timezone.now().date()
            return today.year - self.birth_date.year - (
                    (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
        return None

    @property
    def total_debt_usd(self):
        """Mijozning dollar qarzini hisoblash"""
        from sales.models import Debt
        active_debts = Debt.objects.filter(
            customer=self,
            status='active',
            currency='USD'
        ).aggregate(
            total_debt=Sum('debt_amount'),
            total_paid=Sum('paid_amount')
        )
        total_debt = active_debts['total_debt'] or Decimal('0')
        total_paid = active_debts['total_paid'] or Decimal('0')
        return max(Decimal('0'), total_debt - total_paid)

    @property
    def total_debt_uzs(self):
        """Mijozning so'm qarzini hisoblash"""
        from sales.models import Debt
        active_debts = Debt.objects.filter(
            customer=self,
            status='active',
            currency='UZS'
        ).aggregate(
            total_debt=Sum('debt_amount'),
            total_paid=Sum('paid_amount')
        )
        total_debt = active_debts['total_debt'] or Decimal('0')
        total_paid = active_debts['total_paid'] or Decimal('0')
        return max(Decimal('0'), total_debt - total_paid)

    @property
    def total_purchases_usd(self):
        """Mijozning dollar xaridlarini hisoblash"""
        from sales.models import PhoneSale, PhoneExchange
        phone_sales = self.phone_sales.aggregate(total=Sum('sale_price'))['total'] or Decimal('0')
        phone_exchanges = self.phone_exchanges.aggregate(total=Sum('new_phone_price'))['total'] or Decimal('0')
        return phone_sales + phone_exchanges

    @property
    def total_purchases_uzs(self):
        """Mijozning so'm xaridlarini hisoblash"""
        from sales.models import AccessorySale
        accessory_sales = self.accessory_sales.aggregate(total=Sum('total_price'))['total'] or Decimal('0')
        return accessory_sales

    @property
    def active_debts_count(self):
        """Faol qarzlar soni"""
        from sales.models import Debt
        return Debt.objects.filter(customer=self, status='active').count()

    @property
    def total_paid_amount_usd(self):
        """Umumiy to'langan dollar summa"""
        from sales.models import Debt
        return Debt.objects.filter(customer=self, currency='USD').aggregate(total=Sum('paid_amount'))[
            'total'] or Decimal('0')

    @property
    def total_paid_amount_uzs(self):
        """Umumiy to'langan so'm summa"""
        from sales.models import Debt
        return Debt.objects.filter(customer=self, currency='UZS').aggregate(total=Sum('paid_amount'))[
            'total'] or Decimal('0')

    def get_detailed_phone_sales(self):
        """Mijozning barcha telefon sotib olishlari va to'liq ma'lumotlari"""
        from sales.models import PhoneSale
        detailed_sales = []

        for sale in self.phone_sales.select_related(
                'phone__phone_model',
                'phone__memory_size',
                'phone__supplier',
                'phone__external_seller',
                'phone__daily_seller',
                'phone__created_by',
                'salesman'
        ).order_by('-sale_date'):
            phone = sale.phone
            detailed_sales.append({
                'sale': sale,
                'phone_model': phone.phone_model,
                'memory_size': phone.memory_size,
                'imei': phone.imei,
                'condition': phone.condition_percentage,
                'purchase_price': phone.purchase_price,
                'cost_price': phone.cost_price,
                'sale_price': sale.sale_price,
                'profit': sale.sale_price - phone.cost_price,
                'sale_date': sale.sale_date,
                'salesman': sale.salesman.get_full_name() or sale.salesman.username,
                'supplier': phone.supplier.name if phone.supplier else "Noma'lum",
                'external_seller': phone.external_seller.name if phone.external_seller else None,
                'daily_seller': phone.daily_seller.name if phone.daily_seller else None,
                'source_type': phone.get_source_type_display(),
                'created_by': phone.created_by.get_full_name() if phone.created_by else "Noma'lum",
                'phone_created_at': phone.created_at,
                'payment_methods': {
                    'cash': sale.cash_amount,
                    'card': sale.card_amount,
                    'credit': sale.credit_amount,
                    'debt': sale.debt_amount
                },
                'notes': sale.notes
            })

        return detailed_sales

    def get_detailed_phone_exchanges(self):
        """Mijozning barcha telefon almashtirishlari va to'liq ma'lumotlari"""
        from sales.models import PhoneExchange
        detailed_exchanges = []

        for exchange in self.phone_exchanges.select_related(
                'new_phone__phone_model',
                'new_phone__memory_size',
                'new_phone__supplier',
                'new_phone__external_seller',
                'new_phone__daily_seller',
                'new_phone__created_by',
                'old_phone_model',
                'old_phone_memory',
                'salesman',
                'created_old_phone'
        ).order_by('-exchange_date'):
            detailed_exchanges.append({
                'exchange': exchange,
                'new_phone': exchange.new_phone,
                'new_phone_model': exchange.new_phone.phone_model,
                'new_phone_memory': exchange.new_phone.memory_size,
                'new_phone_imei': exchange.new_phone.imei,
                'new_phone_price': exchange.new_phone_price,
                'old_phone_model': exchange.old_phone_model,
                'old_phone_memory': exchange.old_phone_memory,
                'old_phone_imei': exchange.old_phone_imei,
                'old_phone_accepted_price': exchange.old_phone_accepted_price,
                'exchange_type': exchange.get_exchange_type_display(),
                'price_difference': exchange.price_difference,
                'exchange_date': exchange.exchange_date,
                'salesman': exchange.salesman.get_full_name() or exchange.salesman.username,
                'created_old_phone': exchange.created_old_phone,
                'payment_methods': {
                    'cash': exchange.cash_amount,
                    'card': exchange.card_amount,
                    'credit': exchange.credit_amount,
                    'debt': exchange.debt_amount
                },
                'notes': exchange.notes
            })

        return detailed_exchanges

    def get_purchase_history(self):
        """Xarid tarixi - valyuta bilan"""
        from sales.models import PhoneSale, AccessorySale, PhoneExchange
        purchases = []

        # Telefon sotuvlari ($)
        for sale in self.phone_sales.select_related('phone__phone_model', 'phone__memory_size').order_by('-sale_date'):
            purchases.append({
                'type': 'phone_sale',
                'date': sale.sale_date,
                'item': f"{sale.phone.phone_model} {sale.phone.memory_size}",
                'amount': sale.sale_price,
                'currency': 'USD',
                'currency_symbol': '$',
                'object': sale
            })

        # Aksessuar sotuvlari (so'm)
        for sale in self.accessory_sales.select_related('accessory').order_by('-sale_date'):
            purchases.append({
                'type': 'accessory_sale',
                'date': sale.sale_date,
                'item': f"{sale.accessory.name} x{sale.quantity}",
                'amount': sale.total_price,
                'currency': 'UZS',
                'currency_symbol': 'so\'m',
                'object': sale
            })

        # Telefon almashtirish ($)
        for exchange in self.phone_exchanges.select_related('new_phone__phone_model', 'old_phone_model').order_by(
                '-exchange_date'):
            purchases.append({
                'type': 'phone_exchange',
                'date': exchange.exchange_date,
                'item': f"{exchange.old_phone_model} → {exchange.new_phone.phone_model}",
                'amount': exchange.new_phone_price,
                'currency': 'USD',
                'currency_symbol': '$',
                'object': exchange
            })

        purchases.sort(key=lambda x: x['date'], reverse=True)
        return purchases

    def get_debt_history(self):
        """Qarz tarixi - valyuta bilan"""
        from sales.models import Debt
        return self.debts.select_related('creditor').order_by('-created_at')

