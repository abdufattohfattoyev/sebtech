from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.core.validators import MinValueValidator, RegexValidator, MaxValueValidator
from django.db.models import Sum, F, Q, DecimalField
from django.utils import timezone
from django.contrib.auth.models import User
from shops.models import Shop


def get_current_date():
    """Bugungi sanani qaytaradi (date obyekti)"""
    return timezone.now().date()


class Supplier(models.Model):
    """Taminotchi - telefon/aksessuar yetkazib beruvchi tashkilot"""
    name = models.CharField(max_length=100, verbose_name="Taminotchi nomi")
    phone_number = models.CharField(max_length=15, verbose_name="Telefon raqami")
    notes = models.TextField(null=True, blank=True, verbose_name="Izoh")
    created_at = models.DateField(default=get_current_date, verbose_name="Yaratilgan sana")

    # Qarz maydonlari
    total_debt = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Umumiy qarz ($)",
        help_text="Taminotchiga umumiy qarz miqdori"
    )
    total_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="To'langan ($)",
        help_text="Taminotchiga to'langan umumiy summa"
    )

    class Meta:
        verbose_name = "Taminotchi"
        verbose_name_plural = "Taminotchilar"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.phone_number}"

    @property
    def balance(self):
        """Qoldiq qarz"""
        return self.total_debt

    def update_total_debt(self):
        """Taminotchining umumiy qarzini hisoblash"""
        total = self.phone_set.filter(
            source_type='supplier',
            payment_status__in=['debt', 'partial']
        ).aggregate(
            total=Sum('debt_balance', output_field=DecimalField(max_digits=15, decimal_places=2))
        )['total'] or Decimal('0.00')

        self.total_debt = total
        self.save(update_fields=['total_debt'])
        return total

    def recalculate_debt_and_payments(self):
        """Taminotchining qarz va to'lovlarini qayta hisoblash"""
        # 1. Haqiqiy umumiy qarz (barcha qarzda turgan telefonlar)
        total_debt = self.phone_set.filter(
            source_type='supplier',
            payment_status__in=['debt', 'partial']
        ).aggregate(
            total=Sum('debt_balance', output_field=DecimalField(max_digits=15, decimal_places=2))
        )['total'] or Decimal('0.00')

        # 2. Haqiqiy umumiy to'langan (barcha telefonlar bo'yicha)
        total_paid = self.phone_set.filter(
            source_type='supplier'
        ).aggregate(
            total=Sum('paid_amount', output_field=DecimalField(max_digits=15, decimal_places=2))
        )['total'] or Decimal('0.00')

        # 3. Yangilash
        self.total_debt = total_debt
        self.total_paid = total_paid
        self.save(update_fields=['total_debt', 'total_paid'])

        return {
            'total_debt': total_debt,
            'total_paid': total_paid,
            'balance': total_debt
        }

    def get_debt_phones(self):
        """Qarzda turgan telefonlar"""
        return self.phone_set.filter(
            source_type='supplier',
            payment_status__in=['debt', 'partial']
        ).order_by('created_at')

    def get_paid_phones(self):
        """To'langan telefonlar"""
        return self.phone_set.filter(
            source_type='supplier',
            payment_status='paid'
        ).order_by('-created_at')


class ExternalSeller(models.Model):
    """Tashqi sotuvchi - telefon olib keluvchi jismoniy shaxs (diler)"""
    name = models.CharField(max_length=100, verbose_name="Tashqi sotuvchi ismi")
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        verbose_name="Telefon raqami"
    )
    image = models.ImageField(upload_to='external_sellers/', blank=True, null=True, verbose_name="Rasm")
    notes = models.TextField(null=True, blank=True, verbose_name="Izoh")
    created_at = models.DateField(default=get_current_date, verbose_name="Yaratilgan sana")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name="Qo'shgan foydalanuvchi")

    class Meta:
        verbose_name = "Tashqi sotuvchi (Diler)"
        verbose_name_plural = "Tashqi sotuvchilar (Dilerlar)"

    def __str__(self):
        return f"{self.name} - {self.phone_number}"


class DailySeller(models.Model):
    """Kunlik sotuvchi - telefon olib keluvchi shaxs (kunlik naqd puldan to'lanadi)"""
    name = models.CharField(max_length=100, verbose_name="Kunlik sotuvchi ismi")
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        verbose_name="Telefon raqami"
    )
    notes = models.TextField(null=True, blank=True, verbose_name="Izoh")
    created_at = models.DateField(default=get_current_date, verbose_name="Yaratilgan sana")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name="Qo'shgan foydalanuvchi")

    class Meta:
        verbose_name = "Kunlik sotuvchi"
        verbose_name_plural = "Kunlik sotuvchilar"

    def __str__(self):
        return f"{self.name} - {self.phone_number}"


class PhoneModel(models.Model):
    model_name = models.CharField(max_length=50, unique=True, verbose_name="iPhone modeli")
    created_at = models.DateField(default=get_current_date, verbose_name="Yaratilgan sana")

    class Meta:
        verbose_name = "iPhone modeli"
        verbose_name_plural = "iPhone modellari"
        ordering = ['-created_at']  # Eng yangi birinchi

    def __str__(self):
        return self.model_name


class MemorySize(models.Model):
    size = models.CharField(max_length=20, unique=True, verbose_name="Xotira hajmi")
    created_at = models.DateField(default=get_current_date, verbose_name="Yaratilgan sana")

    class Meta:
        verbose_name = "Xotira hajmi"
        verbose_name_plural = "Xotira hajmlari"

    def __str__(self):
        return self.size


class Accessory(models.Model):
    """Aksessuar - SO'MDA"""
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="accessories", verbose_name="Do'kon")
    name = models.CharField(max_length=100, verbose_name="Aksessuar nomi")
    code = models.CharField(
        max_length=10,
        validators=[RegexValidator(r'^\d+$', "Faqat raqam kiritish mumkin!")],
        verbose_name="Aksessuar kodi",
        db_index=True
    )
    image = models.ImageField(upload_to='accessories/', blank=True, null=True, verbose_name="Rasm")
    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Tannarx (so'm)",
        editable=False,
        default=0
    )
    sale_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Sotish narxi (so'm)"
    )
    quantity = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Soni",
        editable=False
    )
    supplier = models.ForeignKey('Supplier', on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name="Taminotchi")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Qo'shgan foydalanuvchi"
    )
    created_at = models.DateField(default=get_current_date, verbose_name="Yaratilgan sana")

    class Meta:
        verbose_name = "Aksessuar"
        verbose_name_plural = "Aksessuarlar"
        unique_together = [('shop', 'code')]
        indexes = [
            models.Index(fields=['shop', 'code'], name='accessory_shop_code_idx'),
        ]

    def calculate_totals(self):
        """Faqat o'rtacha narxni hisoblash"""
        if not self.pk:
            return 0, Decimal('0.00')

        history = self.purchase_history.all()
        total_quantity = history.aggregate(total=Sum('quantity'))['total'] or 0

        if total_quantity > 0:
            total_cost = history.aggregate(
                total=Sum(F('purchase_price') * F('quantity'),
                          output_field=DecimalField(max_digits=15, decimal_places=2))
            )['total'] or Decimal('0.00')
            average_price = (total_cost / total_quantity).quantize(Decimal('0.01'))
        else:
            average_price = Decimal('0.00')

        return total_quantity, average_price

    def save(self, *args, **kwargs):
        skip_quantity_update = kwargs.pop('skip_quantity_update', False)

        if self.code and self.code.isdigit() and len(self.code) < 4:
            self.code = self.code.zfill(4)

        if self.pk and not skip_quantity_update:
            _, self.purchase_price = self.calculate_totals()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code}) - {self.shop.name}"

    def clean(self):
        super().clean()
        if self.code and self.shop:
            existing = Accessory.objects.filter(shop=self.shop, code=self.code)
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError(f"Bu kod ({self.code}) allaqachon '{self.shop.name}' do'konida mavjud.")

    @classmethod
    def get_next_code(cls, shop):
        last_accessory = cls.objects.filter(shop=shop).order_by('-code').first()
        if last_accessory and last_accessory.code.isdigit():
            next_code = int(last_accessory.code) + 1
            return str(next_code).zfill(4)
        return "0001"

    @classmethod
    def find_by_code(cls, shop, code):
        formatted_code = code.zfill(4) if code.isdigit() else code
        try:
            return cls.objects.get(shop=shop, code=formatted_code)
        except cls.DoesNotExist:
            return None


class AccessoryPurchaseHistory(models.Model):
    """Aksessuar sotib olish tarixi"""
    accessory = models.ForeignKey(
        Accessory,
        on_delete=models.CASCADE,
        related_name="purchase_history",
        verbose_name="Aksessuar"
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Soni"
    )
    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Tannarx (so'm)"
    )
    created_at = models.DateField(default=get_current_date, verbose_name="Qo'shilgan sana")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Qo'shgan foydalanuvchi"
    )

    class Meta:
        verbose_name = "Aksessuar sotib olish tarixi"
        verbose_name_plural = "Aksessuar sotib olish tarixlari"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        is_new = not self.pk
        super().save(*args, **kwargs)

        if is_new and self.accessory_id:
            Accessory.objects.filter(pk=self.accessory_id).update(
                quantity=F('quantity') + self.quantity
            )
            self.accessory.refresh_from_db()
            _, avg_price = self.accessory.calculate_totals()
            Accessory.objects.filter(pk=self.accessory_id).update(
                purchase_price=avg_price
            )

    def __str__(self):
        return f"{self.accessory.name} - {self.quantity} dona, {self.purchase_price} so'm ({self.created_at})"


class Phone(models.Model):
    """Telefon - DOLLARDA"""
    STATUS_CHOICES = [
        ('shop', "Do'konda"),
        ('master', "Ustada"),
        ('sold', "Sotilgan"),
        ('returned', "Qaytarilgan"),
        ('exchanged_in', "Almashtirishda qabul qilingan"),
    ]
    SOURCE_CHOICES = [
        ('supplier', 'Taminotchi'),
        ('external_seller', 'Tashqi sotuvchi (Diler)'),
        ('daily_seller', 'Kunlik sotuvchi'),
        ('exchange', 'Almashtirish'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('paid', 'To\'langan'),
        ('debt', 'Qarzda'),
        ('partial', 'Qisman to\'langan'),
    ]

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="phones", verbose_name="Do'kon")
    phone_model = models.ForeignKey('PhoneModel', on_delete=models.CASCADE, verbose_name="iPhone modeli")
    memory_size = models.ForeignKey('MemorySize', on_delete=models.CASCADE, verbose_name="Xotira hajmi")
    imei = models.CharField(
        max_length=20,
        verbose_name="IMEI",
        db_index=True,
        validators=[RegexValidator(r'^\d{15}$', "IMEI 15 ta raqamdan iborat bo'lishi kerak")]
    )
    condition_percentage = models.IntegerField(
        default=100,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        verbose_name="Holati (%)"
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='shop',
        verbose_name="Holati",
        db_index=True
    )
    purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Sotib olingan narx ($)"
    )
    imei_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="IMEI xarajatlari ($)"
    )
    repair_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Ta'mirlash xarajatlari ($)"
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False,
        verbose_name="Tan narx ($)"
    )
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Sotish narxi ($)"
    )
    image = models.ImageField(upload_to='phones/', blank=True, null=True, verbose_name="Rasm")
    created_at = models.DateField(verbose_name="Yaratilgan sana")
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Qo'shgan foydalanuvchi"
    )
    note = models.TextField(
        blank=True,
        null=True,
        verbose_name="Izoh",
        help_text="Telefon haqida qo'shimcha ma'lumot"
    )
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default='supplier',
        verbose_name="Manba turi"
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Taminotchi"
    )
    external_seller = models.ForeignKey(
        'ExternalSeller',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Tashqi sotuvchi (Diler)",
        related_name="supplied_phones"
    )
    daily_seller = models.ForeignKey(
        'DailySeller',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Kunlik sotuvchi",
        related_name="sold_phones"
    )
    daily_payment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Kunlik sotuvchiga to'langan summa ($)"
    )
    daily_payment_expense = models.ForeignKey(
        'sales.Expense',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='daily_seller_phones',
        verbose_name="Bog'langan xarajat"
    )
    exchange_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Almashtirish qiymati ($)"
    )
    original_owner_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Asl egasi ismi"
    )
    original_owner_phone = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        verbose_name="Asl egasi telefon raqami"
    )

    # QARZ MAYDONLARI
    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS_CHOICES,
        default='paid',
        verbose_name="To'lov holati",
        db_index=True
    )
    paid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="To'langan summa ($)",
        help_text="Bu telefonга to'langan summa"
    )
    debt_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Qarz qoldig'i ($)",
        help_text="Bu telefon uchun qolgan qarz"
    )

    class Meta:
        verbose_name = "Telefon"
        verbose_name_plural = "Telefonlar"
        indexes = [
            models.Index(fields=['imei'], name='phone_imei_idx'),
            models.Index(fields=['status'], name='phone_status_idx'),
            models.Index(fields=['shop', 'status'], name='phone_shop_status_idx'),
            models.Index(fields=['payment_status'], name='phone_payment_status_idx'),
            models.Index(fields=['supplier', 'payment_status'], name='phone_supplier_payment_idx'),
        ]

    def __str__(self):
        return f"{self.phone_model} {self.memory_size} - IMEI: {self.imei or 'N/A'}"

    def save(self, *args, **kwargs):
        # Cost price hisoblash
        self.cost_price = self.purchase_price + self.imei_cost + self.repair_cost

        # Qarz balansini hisoblash
        if self.source_type == 'supplier':
            self.debt_balance = self.cost_price - self.paid_amount

            # To'lov holatini yangilash
            if self.paid_amount >= self.cost_price:
                self.payment_status = 'paid'
                self.debt_balance = Decimal('0')
            elif self.paid_amount > 0:
                self.payment_status = 'partial'
            else:
                self.payment_status = 'debt'
        else:
            # Boshqa manbalar uchun avtomatik to'langan
            self.payment_status = 'paid'
            self.paid_amount = self.cost_price
            self.debt_balance = Decimal('0')

        is_new = self.pk is None
        old_supplier = None
        old_debt = Decimal('0')

        # Agar tahrirlash bo'lsa, eski qiymatlarni saqlash
        if not is_new:
            try:
                old_phone = Phone.objects.get(pk=self.pk)
                old_supplier = old_phone.supplier
                old_debt = old_phone.debt_balance
            except Phone.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        # Taminotchining umumiy qarzini yangilash
        if self.source_type == 'supplier' and self.supplier:
            self.supplier.update_total_debt()

        # Agar supplier o'zgargan bo'lsa, eski supplier qarzini ham yangilash
        if old_supplier and old_supplier != self.supplier:
            old_supplier.update_total_debt()

    def clean(self):
        super().clean()

        if not self.created_at:
            raise ValidationError({'created_at': "Qo'shilgan sana kiritilishi shart!"})

        if not self.imei or not self.imei.strip():
            raise ValidationError({'imei': "IMEI kiritilishi shart!"})

        if self.source_type == 'supplier' and not self.supplier:
            raise ValidationError({'supplier': "Taminotchi manba turi uchun taminotchi tanlanishi kerak."})

        if self.source_type == 'external_seller' and not self.external_seller:
            raise ValidationError(
                {'external_seller': "Tashqi sotuvchi manba turi uchun tashqi sotuvchi tanlanishi kerak."})

        if self.source_type == 'daily_seller':
            if not self.daily_payment_amount or self.daily_payment_amount <= 0:
                raise ValidationError({'daily_payment_amount': "Kunlik sotuvchiga to'langan summa kiritilishi kerak."})

        if self.source_type == 'exchange' and not (self.original_owner_name and self.original_owner_phone):
            raise ValidationError({
                'original_owner_name': "Almashtirish manbasi uchun asl egasi ismi kiritilishi kerak.",
                'original_owner_phone': "Almashtirish manbasi uchun telefon raqami kiritilishi kerak."
            })


class SupplierPayment(models.Model):
    """Taminotchiga to'lov"""
    PAYMENT_TYPE_CHOICES = [
        ('general', 'Umumiy to\'lov (FIFO)'),
        ('specific', 'Tanlangan telefonlar'),
    ]

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name="Taminotchi"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="To'lov summasi ($)"
    )
    payment_type = models.CharField(
        max_length=10,
        choices=PAYMENT_TYPE_CHOICES,
        default='general',
        verbose_name="To'lov turi"
    )
    payment_date = models.DateField(
        default=get_current_date,
        verbose_name="To'lov sanasi"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Izoh"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Amalga oshirgan"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Yaratilgan vaqt"
    )

    class Meta:
        verbose_name = "Taminotchiga to'lov"
        verbose_name_plural = "Taminotchiga to'lovlar"
        ordering = ['-payment_date', '-created_at']

    def __str__(self):
        return f"{self.supplier.name} - ${self.amount} ({self.payment_date})"


class SupplierPaymentDetail(models.Model):
    """To'lov tafsiloti - qaysi telefonga qancha to'landi"""
    payment = models.ForeignKey(
        SupplierPayment,
        on_delete=models.CASCADE,
        related_name='details',
        verbose_name="To'lov"
    )
    phone = models.ForeignKey(
        Phone,
        on_delete=models.CASCADE,
        related_name='payment_details',
        verbose_name="Telefon"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Bu telefonga to'langan ($)"
    )
    previous_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Oldingi qarz ($)"
    )
    new_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Yangi qarz ($)"
    )

    class Meta:
        verbose_name = "To'lov tafsiloti"
        verbose_name_plural = "To'lov tafsilotlari"
        ordering = ['payment', 'phone']

    def __str__(self):
        return f"{self.phone} - ${self.amount}"