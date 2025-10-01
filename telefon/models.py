from django.db import models
from django.contrib.auth.models import User, Group
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from decimal import Decimal
from django.db.models import F, Sum, ExpressionWrapper, DecimalField
from django.utils.timezone import now
from datetime import datetime
import calendar


# Foydalanuvchi profili
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('boss', 'Boshliq (Ega)'),
        ('finance', 'Moliyachi'),
        ('seller', 'Sotuvchi'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Foydalanuvchi")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='seller', verbose_name="Rol")
    phone_number = models.CharField(max_length=15, null=True, blank=True, verbose_name="Telefon raqami")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")

    class Meta:
        verbose_name = "Foydalanuvchi profili"
        verbose_name_plural = "Foydalanuvchi profillari"

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.get_role_display()}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        group_name = f"{self.role}s"
        if self.role == 'boss':
            group_name = 'bosses'
        elif self.role == 'finance':
            group_name = 'financiers'
        elif self.role == 'seller':
            group_name = 'sellers'

        group, created = Group.objects.get_or_create(name=group_name)
        self.user.groups.clear()
        self.user.groups.add(group)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.userprofile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)


# Do'konlar
class Shop(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Do'kon nomi")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'userprofile__role': 'boss'},
                              verbose_name="Do'kon egasi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")

    class Meta:
        verbose_name = "Do'kon"
        verbose_name_plural = "Do'konlar"

    def __str__(self):
        return self.name


# Mijozlar
class Customer(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="customers", verbose_name="Do'kon")
    name = models.CharField(max_length=100, verbose_name="Mijoz ismi")
    phone_number = models.CharField(max_length=15, verbose_name="Telefon raqami")
    image = models.ImageField(upload_to='customers/', blank=True, null=True, verbose_name="Mijoz rasmi")
    address = models.TextField(null=True, blank=True, verbose_name="Manzil")
    notes = models.TextField(null=True, blank=True, verbose_name="Izohlar")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Qo'shilgan sana")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name="Qo'shgan foydalanuvchi")

    class Meta:
        verbose_name = "Mijoz"
        verbose_name_plural = "Mijozlar"
        unique_together = ['shop', 'phone_number']

    def __str__(self):
        return f"{self.name} - {self.phone_number}"

    @property
    def total_purchases(self):
        phone_purchases = self.phone_sales.aggregate(
            total=Sum('sale_price')
        )['total'] or 0
        accessory_purchases = self.accessory_sales.aggregate(
            total=Sum('total_sale_price')
        )['total'] or 0
        exchange_purchases = self.phone_exchanges.aggregate(
            total=Sum('new_phone_price')
        )['total'] or 0
        return phone_purchases + accessory_purchases + exchange_purchases

    @property
    def total_debt(self):
        result = self.debts.filter(status='active').aggregate(
            total=Sum(ExpressionWrapper(F('debt_amount') - F('paid_amount'), output_field=DecimalField()))
        )
        return result['total'] or 0

    @property
    def purchased_phones(self):
        return self.phone_sales.all()

    @property
    def last_purchase_date(self):
        last_phone = self.phone_sales.order_by('-created_at').first()
        last_accessory = self.accessory_sales.order_by('-created_at').first()
        last_exchange = self.phone_exchanges.order_by('-created_at').first()
        dates = [date.created_at for date in [last_phone, last_accessory, last_exchange] if date]
        return max(dates) if dates else None


# Taminotchilar
class Supplier(models.Model):
    name = models.CharField(max_length=100, verbose_name="Taminotchi nomi")
    phone_number = models.CharField(max_length=15, verbose_name="Telefon raqami")
    address = models.TextField(null=True, blank=True, verbose_name="Manzil")
    notes = models.TextField(null=True, blank=True, verbose_name="Izoh")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")

    class Meta:
        verbose_name = "Taminotchi"
        verbose_name_plural = "Taminotchilar"

    def __str__(self):
        return f"{self.name} - {self.phone_number}"


# Telefon modellari
class PhoneModel(models.Model):
    model_name = models.CharField(max_length=50, unique=True, verbose_name="iPhone modeli")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")

    class Meta:
        verbose_name = "iPhone modeli"
        verbose_name_plural = "iPhone modellari"

    def __str__(self):
        return self.model_name


# Xotira hajmlari
class MemorySize(models.Model):
    size = models.CharField(max_length=20, unique=True, verbose_name="Xotira hajmi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")

    class Meta:
        verbose_name = "Xotira hajmi"
        verbose_name_plural = "Xotira hajmlari"

    def __str__(self):
        return self.size


# Aksessuarlar
class Accessory(models.Model):
    shop = models.ForeignKey("Shop", on_delete=models.CASCADE, related_name="accessories", verbose_name="Do'kon")
    name = models.CharField(max_length=100, verbose_name="Aksessuar nomi")
    code = models.CharField(
        max_length=10,
        unique=True,
        validators=[RegexValidator(r'^\d+$', "Faqat raqam kiritish mumkin!")],
        verbose_name="Aksessuar kodi"
    )
    image = models.ImageField(upload_to='accessories/', blank=True, null=True, verbose_name="Rasm")
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)],
                                         verbose_name="Tannarx")
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)],
                                     verbose_name="Sotish narxi")
    quantity = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], verbose_name="Soni")
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, verbose_name="Taminotchi")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name="Qo'shgan foydalanuvchi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")

    class Meta:
        verbose_name = "Aksessuar"
        verbose_name_plural = "Aksessuarlar"

    def save(self, *args, **kwargs):
        if self.code.isdigit():
            self.code = self.code.zfill(4)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})"


# Ustalar
class Master(models.Model):
    first_name = models.CharField(max_length=50, verbose_name="Ism")
    last_name = models.CharField(max_length=50, verbose_name="Familiya")
    phone_number = models.CharField(max_length=15, verbose_name="Telefon raqami")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")

    class Meta:
        verbose_name = "Usta"
        verbose_name_plural = "Ustalar"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def total_unpaid_amount(self):
        return self.master_services.filter(
            status='in_progress'
        ).aggregate(
            total_unpaid=Sum('service_fee')
        )['total_unpaid'] or 0

    @property
    def active_repairs(self):
        return self.master_services.filter(status='in_progress')

    @property
    def completed_repairs(self):
        return self.master_services.filter(status='completed')

    @property
    def active_repairs_count(self):
        return self.active_repairs.count()

    @property
    def overdue_repairs_count(self):
        return self.active_repairs.filter(
            expected_return_date__lt=timezone.now().date()
        ).count()


# Usta xizmatlari
class MasterService(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'Jarayonda'),
        ('completed', 'Tugallangan'),
    ]

    phone = models.ForeignKey('Phone', on_delete=models.CASCADE, related_name="master_services", verbose_name="Telefon")
    master = models.ForeignKey(Master, on_delete=models.CASCADE, related_name="master_services", verbose_name="Usta")
    service_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        verbose_name="Xizmat haqi"
    )
    paid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        verbose_name="To'langan summa"
    )
    debt = models.OneToOneField('Debt', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="master_service", verbose_name="Bog'langan qarz")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='in_progress', verbose_name="Holati")
    repair_reasons = models.TextField(verbose_name="Ta'mirlash sabablari",
                                      help_text="Ta'mirlash sabablari va kerakli ishlarni kiriting")
    given_date = models.DateField(default=timezone.now, verbose_name="Ustaga berilgan sana")
    expected_return_date = models.DateField(null=True, blank=True, verbose_name="Qaytarish rejalashtirilgan sana")
    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
        verbose_name="Yaratilgan vaqt"
    )

    class Meta:
        verbose_name = "Usta xizmati"
        verbose_name_plural = "Usta xizmatlari"

    def __str__(self):
        return f"{self.master} - {self.phone} - {self.service_fee}$ ({self.get_status_display()})"

    @property
    def remaining_amount(self):
        return self.service_fee - self.paid_amount

    @property
    def is_overdue(self):
        if self.expected_return_date and self.status == 'in_progress':
            return timezone.now().date() > self.expected_return_date
        return False

    def clean(self):
        if not self.repair_reasons or not self.repair_reasons.strip():
            raise ValidationError({'repair_reasons': "Ta'mirlash sabablari kiritilishi shart!"})
        if self.given_date and self.given_date > timezone.now().date():
            raise ValidationError({'given_date': "Ustaga berilgan sana bugundan kech bo'lmasligi kerak!"})
        if self.expected_return_date and self.given_date and self.expected_return_date < self.given_date:
            raise ValidationError({'expected_return_date': "Qaytarish sanasi berilgan sanadan kech bo'lishi kerak!"})

    def save(self, *args, **kwargs):
        # Telefon holatini yangilash
        if self.status == 'in_progress':
            self.phone.status = 'master'
        elif self.status == 'completed':
            self.phone.status = 'shop'

        # Telefon ta'mirlash xarajatini yangilash (faqat yangi obyekt uchun)
        if not self.pk:  # Yangi obyekt
            self.phone.repair_cost += self.service_fee
        else:  # Mavjud obyektni yangilash
            # Eski qiymatni olib, yangi qiymatni qo'shish
            old_instance = MasterService.objects.get(pk=self.pk)
            self.phone.repair_cost = self.phone.repair_cost - old_instance.service_fee + self.service_fee

        self.phone.save()

        # Qarz boshqaruvi
        if self.service_fee > 0 and self.paid_amount < self.service_fee:
            remaining_amount = self.service_fee - self.paid_amount

            if not self.debt:
                # Yangi qarz yaratish
                shop_owner = self.phone.shop.owner
                self.debt = Debt.objects.create(
                    debt_type='master_service',
                    creditor=shop_owner,
                    debtor_user=None,
                    customer=None,
                    debt_amount=remaining_amount,
                    paid_amount=0,
                    notes=f"Usta xizmati qarzi: {self.master} - {self.phone} ({self.service_fee}$)"
                )
            else:
                # Mavjud qarzni yangilash
                self.debt.debt_amount = remaining_amount
                self.debt.paid_amount = self.paid_amount
                if self.debt.paid_amount >= self.debt.debt_amount:
                    self.debt.status = 'paid'
                else:
                    self.debt.status = 'active'
                self.debt.save()
        elif self.paid_amount >= self.service_fee:
            # To'liq to'langan bo'lsa, qarzni o'chirish
            if self.debt:
                self.debt.delete()
                self.debt = None

        super().save(*args, **kwargs)


# Usta to'lovlari
class MasterPayment(models.Model):
    master_service = models.ForeignKey(MasterService, on_delete=models.CASCADE, related_name="payments",
                                       verbose_name="Usta xizmati")
    payment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="To'lov summasi"
    )
    payment_date = models.DateTimeField(auto_now_add=True, verbose_name="To'lov sanasi")
    paid_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="To'lovchi")
    notes = models.TextField(null=True, blank=True, verbose_name="Izoh")

    class Meta:
        verbose_name = "Usta to'lovi"
        verbose_name_plural = "Usta to'lovlari"

    def __str__(self):
        return f"{self.master_service.master} - {self.payment_amount}$ ({self.master_service.phone})"

    def clean(self):
        if self.payment_amount <= 0:
            raise ValidationError({'payment_amount': "To'lov summasi 0 dan katta bo'lishi kerak!"})

        # Umumiy to'lovlar service_fee dan oshmasligi kerakligini tekshirish
        total_payments = self.master_service.payments.exclude(pk=self.pk).aggregate(
            total=models.Sum('payment_amount')
        )['total'] or 0

        if total_payments + self.payment_amount > self.master_service.service_fee:
            remaining = self.master_service.service_fee - total_payments
            raise ValidationError({
                'payment_amount': f"To'lov summasi {remaining}$ dan oshmasligi kerak! (Qolgan qarz: {remaining}$)"
            })

    def save(self, *args, **kwargs):
        # Validatsiya
        self.full_clean()

        super().save(*args, **kwargs)

        # Umumiy to'lovni hisoblash va yangilash
        total_paid = self.master_service.payments.aggregate(
            total=models.Sum('payment_amount')
        )['total'] or 0

        self.master_service.paid_amount = total_paid
        self.master_service.save()


# Telefonlar
class Phone(models.Model):
    STATUS_CHOICES = [
        ('shop', "Do'konda"),
        ('master', "Ustada"),
        ('sold', "Sotilgan"),
        ('returned', "Qaytarilgan"),
        ('exchanged_in', "Almashtirishda qabul qilingan"),
    ]
    SOURCE_CHOICES = [
        ('supplier', 'Taminotchi'),
        ('client', 'Mijoz'),
        ('exchange', 'Almashtirish'),
        ('daily_client', 'Kunlik mijoz'),
    ]

    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="phones", verbose_name="Do'kon")
    phone_model = models.ForeignKey(PhoneModel, on_delete=models.CASCADE, verbose_name="iPhone modeli")
    memory_size = models.ForeignKey(MemorySize, on_delete=models.CASCADE, verbose_name="Xotira hajmi")
    imei = models.CharField(max_length=20, null=True, blank=True, verbose_name="IMEI")
    condition_percentage = models.IntegerField(default=100, validators=[MinValueValidator(1), MaxValueValidator(100)],
                                               verbose_name="Holati (%)")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='shop', verbose_name="Holati")
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Sotib olingan narx")
    imei_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="IMEI xarajatlari")
    repair_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ta'mirlash xarajatlari")
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False, verbose_name="Tan narx")
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     verbose_name="Sotish narxi")
    image = models.ImageField(upload_to='phones/', blank=True, null=True, verbose_name="Rasm")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name="Qo'shgan foydalanuvchi")
    source_type = models.CharField(max_length=15, choices=SOURCE_CHOICES, default='supplier', verbose_name="Manba turi")
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Taminotchi")
    client_name = models.CharField(max_length=100, null=True, blank=True, verbose_name="Mijoz ismi")
    client_phone_number = models.CharField(max_length=15, null=True, blank=True, verbose_name="Mijoz telefon raqami")
    exchange_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                         verbose_name="Almashtirish qiymati")
    original_owner_name = models.CharField(max_length=100, null=True, blank=True,
                                           verbose_name="Asl egasi ismi")
    original_owner_phone = models.CharField(max_length=15, null=True, blank=True,
                                            verbose_name="Asl egasi telefon raqami")

    class Meta:
        verbose_name = "Telefon"
        verbose_name_plural = "Telefonlar"

    def __str__(self):
        return f"{self.phone_model} {self.memory_size} - IMEI: {self.imei or 'IMEI yoq'} - {self.shop}"

    def save(self, *args, **kwargs):
        self.cost_price = self.purchase_price + self.imei_cost + self.repair_cost
        super().save(*args, **kwargs)

    def clean(self):
        if self.source_type == 'supplier' and not self.supplier:
            raise ValidationError("Taminotchidan olingan telefon uchun taminotchi tanlanishi shart!")
        if self.source_type in ['client', 'daily_client'] and (not self.client_name or not self.client_phone_number):
            raise ValidationError("Mijozdan olingan telefon uchun mijoz ismi va telefon raqami kiritilishi shart!")
        if self.source_type == 'exchange' and (not self.original_owner_name or not self.original_owner_phone):
            raise ValidationError("Almashtirishdan olingan telefon uchun asl egasi ma'lumotlari kiritilishi shart!")


# Qarzlar tizimi
class Debt(models.Model):
    DEBT_TYPE_CHOICES = [
        ('phone_customer', 'Telefon - Mijoz qarzni'),
        ('accessory_customer', 'Aksessuar - Mijoz qarzni'),
        ('phone_seller', 'Telefon - Sotuvchi qarzni'),
        ('accessory_seller', 'Aksessuar - Sotuvchi qarzni'),
        ('master_service', 'Usta xizmati qarzni'),
    ]
    DEBT_STATUS_CHOICES = [
        ('active', 'Faol'),
        ('paid', "To'langan"),
        ('cancelled', 'Bekor qilingan'),
    ]

    debt_type = models.CharField(max_length=30, choices=DEBT_TYPE_CHOICES, verbose_name="Qarz turi")
    creditor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="given_debts",
                                 verbose_name="Qarz bergan")
    debtor_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_debts",
                                    null=True, blank=True, verbose_name="Qarzni olgan foydalanuvchi")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="debts",
                                 null=True, blank=True, verbose_name="Mijoz")
    debt_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,
                                      validators=[MaxValueValidator(500)], verbose_name="Qarz summasi (max 500$)")
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="To'langan summa")
    status = models.CharField(max_length=10, choices=DEBT_STATUS_CHOICES, default='active', verbose_name="Holati")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Qarz berilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")

    # Related objects
    related_phone_sale = models.ForeignKey('PhoneSale', on_delete=models.CASCADE, null=True, blank=True,
                                           verbose_name="Bog'langan telefon sotish")
    related_accessory_sale = models.ForeignKey('AccessorySale', on_delete=models.CASCADE, null=True, blank=True,
                                               verbose_name="Bog'langan aksessuar sotish")
    related_phone_exchange = models.ForeignKey('PhoneExchange', on_delete=models.CASCADE, null=True, blank=True,
                                               verbose_name="Bog'langan telefon almashtirish")
    notes = models.TextField(null=True, blank=True, verbose_name="Izoh")

    class Meta:
        verbose_name = "Qarz"
        verbose_name_plural = "Qarzlar"

    def __str__(self):
        remaining = self.remaining_amount
        if self.customer:
            debtor_name = self.customer.name
        elif self.debtor_user:
            debtor_name = self.debtor_user.get_full_name() or self.debtor_user.username
        else:
            debtor_name = "Noma'lum"
        return f"{debtor_name} - {remaining:,.0f}$ ({self.get_debt_type_display()})"

    @property
    def remaining_amount(self):
        debt_amount = self.debt_amount or Decimal('0.00')
        paid_amount = self.paid_amount or Decimal('0.00')
        return debt_amount - paid_amount

    def clean(self):
        if not self.debtor_user and not self.customer:
            raise ValidationError("Qarzni olgan shaxs (mijoz yoki foydalanuvchi) kiritilishi kerak!")
        if self.debtor_user and self.customer:
            raise ValidationError("Foydalanuvchi va mijoz bir vaqtda kiritilmasligi kerak!")
        if self.debt_amount > 500:
            raise ValidationError("Qarz summasi 500$ dan oshmasligi kerak!")

    def save(self, *args, **kwargs):
        if self.paid_amount >= self.debt_amount:
            self.status = 'paid'
        else:
            self.status = 'active'
        super().save(*args, **kwargs)


# Qarz to'lovlari
class DebtPayment(models.Model):
    debt = models.ForeignKey(Debt, on_delete=models.CASCADE, related_name="payments", verbose_name="Qarz")
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="To'lov summasi")
    payment_date = models.DateTimeField(auto_now_add=True, verbose_name="To'lov sanasi")
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Qabul qilgan")
    notes = models.TextField(null=True, blank=True, verbose_name="Izoh")

    class Meta:
        verbose_name = "Qarz to'lovi"
        verbose_name_plural = "Qarz to'lovlari"

    def __str__(self):
        if self.debt.customer:
            debtor_name = self.debt.customer.name
        elif self.debt.debtor_user:
            debtor_name = self.debt.debtor_user.get_full_name() or self.debt.debtor_user.username
        else:
            debtor_name = "Noma'lum"
        return f"{debtor_name} - {self.payment_amount:,.0f}$ to'lovi"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        total_paid = self.debt.payments.aggregate(models.Sum('payment_amount'))['payment_amount__sum'] or 0
        self.debt.paid_amount = total_paid
        self.debt.save()


# Telefon sotish
class PhoneSale(models.Model):
    phone = models.OneToOneField(Phone, on_delete=models.CASCADE, verbose_name="Telefon")
    phone_cost_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False,
                                           verbose_name="Kirimdagi tan narx (faqat ko'rish uchun)")
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Umumiy sotish narxi")
    cash_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Naqd")
    card_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Karta")
    credit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Nasiya savdo")
    debt_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                      validators=[MaxValueValidator(500)], verbose_name="Qarz daftar (max 500$)")
    salesman = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Sotuvchi")
    customer_name = models.CharField(max_length=100, verbose_name="Mijoz ismi")
    customer_phone = models.CharField(max_length=15, verbose_name="Mijoz telefon raqami")
    customer_address = models.TextField(null=True, blank=True, verbose_name="Mijoz manzili")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="phone_sales", verbose_name="Bog'langan mijoz")
    customer_debt = models.OneToOneField(Debt, on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name="customer_phone_sale", verbose_name="Mijoz qarzni")
    seller_debt = models.OneToOneField(Debt, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name="seller_phone_sale", verbose_name="Sotuvchi qarzni")
    notes = models.TextField(null=True, blank=True, verbose_name="Izoh")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="O'zgartirilgan sana")

    class Meta:
        verbose_name = "Telefon sotish"
        verbose_name_plural = "Telefon sotuvlari"

    def __str__(self):
        return f"{self.phone} - {self.customer_name} - Sotish narxi: {self.sale_price}$"

    @property
    def profit(self):
        """Foyda hisoblagich - sotish narxi minus tan narx"""
        return self.sale_price - self.phone_cost_price

    @property
    def profit_percentage(self):
        """Foyda foizi"""
        if self.phone_cost_price > 0:
            return (self.profit / self.phone_cost_price) * 100
        return 0

    def clean(self):
        if not self.phone:
            raise ValidationError("Telefon tanlanishi shart!")
        if not self.salesman:
            raise ValidationError("Sotuvchi tanlanishi shart!")
        if not self.customer_name or not self.customer_phone:
            raise ValidationError("Mijoz ismi va telefon raqami kiritilishi shart!")

        # To'lovlar yig'indisini tekshirish
        total_payments = self.cash_amount + self.card_amount + self.credit_amount + self.debt_amount
        if abs(total_payments - self.sale_price) > 0.01:
            raise ValidationError(
                f"To'lovlar yig'indisi ({total_payments}) umumiy sotish narxiga ({self.sale_price}) teng bo'lishi kerak!"
            )

    def save(self, *args, **kwargs):
        # Validatsiya
        self.full_clean()

        # Mijozni yaratish yoki yangilash
        if not self.customer:
            try:
                existing_customer = Customer.objects.get(
                    phone_number=self.customer_phone,
                    shop=self.phone.shop
                )
                self.customer = existing_customer
                if existing_customer.name != self.customer_name:
                    existing_customer.name = self.customer_name
                    if self.customer_address:
                        existing_customer.address = self.customer_address
                    existing_customer.save()
            except Customer.DoesNotExist:
                self.customer = Customer.objects.create(
                    shop=self.phone.shop,
                    name=self.customer_name,
                    phone_number=self.customer_phone,
                    address=self.customer_address or "",
                    created_by=self.salesman
                )

        # Telefon ma'lumotlarini saqlash
        self.phone_cost_price = self.phone.cost_price

        # Telefon holatini o'zgartirish
        self.phone.status = 'sold'
        self.phone.save()

        super().save(*args, **kwargs)

        # Qarzlarni boshqarish
        shop_owner = self.phone.shop.owner

        if self.debt_amount > 0:
            # Mijoz qarzni yaratish yoki yangilash
            if not self.customer_debt:
                self.customer_debt = Debt.objects.create(
                    debt_type='phone_customer',
                    creditor=shop_owner,
                    customer=self.customer,
                    debt_amount=self.debt_amount,
                    related_phone_sale=self,
                    notes=f"Mijoz telefon qarzi: {self.phone}"
                )
                # OneToOne field uchun qayta saqlash
                super().save(*args, **kwargs)

            # Sotuvchi qarzni yaratish (agar sotuvchi boshliq bo'lmasa)
            if self.salesman != shop_owner and not self.seller_debt:
                self.seller_debt = Debt.objects.create(
                    debt_type='phone_seller',
                    creditor=shop_owner,
                    debtor_user=self.salesman,
                    debt_amount=self.debt_amount,
                    related_phone_sale=self,
                    notes=f"Sotuvchi telefon qarzi: {self.phone} (Mijoz: {self.customer.name})"
                )
                # OneToOne field uchun qayta saqlash
                super().save(*args, **kwargs)
        else:
            # Qarz yo'q bo'lsa, mavjud qarzlarni o'chirish
            if self.customer_debt and self.customer_debt.paid_amount == 0:
                self.customer_debt.delete()
                self.customer_debt = None
            if self.seller_debt and self.seller_debt.paid_amount == 0:
                self.seller_debt.delete()
                self.seller_debt = None
            if not self.debt_amount:  # Agar qarz 0 bo'lsa qayta saqlash
                super().save(*args, **kwargs)


# Aksessuar sotish
class AccessorySale(models.Model):
    accessory = models.ForeignKey(Accessory, on_delete=models.CASCADE, related_name="sales", verbose_name="Aksessuar")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name="Soni")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Birlik narxi")
    unit_cost_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False,
                                          verbose_name="Birlik tan narxi")
    total_sale_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Umumiy sotish narxi")
    total_cost_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False,
                                           verbose_name="Umumiy tan narx")
    cash_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Naqd")
    card_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Karta")
    debt_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                      validators=[MaxValueValidator(500)], verbose_name="Qarz (max 500$)")
    salesman = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Sotuvchi")
    customer_name = models.CharField(max_length=100, verbose_name="Mijoz ismi")
    customer_phone = models.CharField(max_length=15, verbose_name="Mijoz telefon raqami")
    customer_address = models.TextField(null=True, blank=True, verbose_name="Mijoz manzili")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="accessory_sales", verbose_name="Bog'langan mijoz")
    customer_debt = models.OneToOneField(Debt, on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name="customer_accessory_sale", verbose_name="Mijoz qarzni")
    seller_debt = models.OneToOneField(Debt, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name="seller_accessory_sale", verbose_name="Sotuvchi qarzni")
    notes = models.TextField(null=True, blank=True, verbose_name="Izoh")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="O'zgartirilgan sana")

    class Meta:
        verbose_name = "Aksessuar sotish"
        verbose_name_plural = "Aksessuar sotuvlari"

    def __str__(self):
        return f"{self.accessory.name} - {self.quantity} dona - {self.total_sale_price}$"

    @property
    def profit(self):
        """Foyda hisoblagich - sotish narxi minus tan narx"""
        return self.total_sale_price - self.total_cost_price

    @property
    def profit_percentage(self):
        """Foyda foizi"""
        if self.total_cost_price > 0:
            return (self.profit / self.total_cost_price) * 100
        return 0

    def clean(self):
        if self.quantity > self.accessory.quantity:
            raise ValidationError(f"Aksessuar soni yetarli emas! Mavjud: {self.accessory.quantity}")

        # Umumiy narxni tekshirish
        expected_total = self.unit_price * self.quantity
        if abs(self.total_sale_price - expected_total) > 0.01:
            raise ValidationError(f"Umumiy narx {expected_total}$ bo'lishi kerak!")

        # To'lovlar yig'indisini tekshirish
        total_payments = self.cash_amount + self.card_amount + self.debt_amount
        if abs(total_payments - self.total_sale_price) > 0.01:
            raise ValidationError(
                f"To'lovlar yig'indisi ({total_payments}) umumiy sotish narxiga ({self.total_sale_price}) teng bo'lishi kerak!"
            )

    def save(self, *args, **kwargs):
        # Validatsiya
        self.full_clean()

        # Birlik narxini aksessuar narxidan olish (agar kiritilmagan bo'lsa)
        if not self.unit_price:
            self.unit_price = self.accessory.sale_price

        # Tan narxlarni saqlash
        self.unit_cost_price = self.accessory.purchase_price

        # Umumiy narxlarni hisoblash
        self.total_sale_price = self.unit_price * self.quantity
        self.total_cost_price = self.unit_cost_price * self.quantity

        # Aksessuar sonini kamaytirish (faqat yangi sotish uchun)
        if not self.pk:
            self.accessory.quantity -= self.quantity
            self.accessory.save()

        # Mijozni yaratish yoki topish
        if not self.customer:
            try:
                existing_customer = Customer.objects.get(
                    phone_number=self.customer_phone,
                    shop=self.accessory.shop
                )
                self.customer = existing_customer
            except Customer.DoesNotExist:
                self.customer = Customer.objects.create(
                    shop=self.accessory.shop,
                    name=self.customer_name,
                    phone_number=self.customer_phone,
                    address=self.customer_address or "",
                    created_by=self.salesman
                )

        super().save(*args, **kwargs)

        # Qarzlarni boshqarish
        shop_owner = self.accessory.shop.owner

        if self.debt_amount > 0:
            # Mijoz qarzni yaratish
            if not self.customer_debt:
                self.customer_debt = Debt.objects.create(
                    debt_type='accessory_customer',
                    creditor=shop_owner,
                    customer=self.customer,
                    debt_amount=self.debt_amount,
                    related_accessory_sale=self,
                    notes=f"Mijoz aksessuar qarzi: {self.accessory.name} ({self.quantity} dona)"
                )
                super().save(*args, **kwargs)

            # Sotuvchi qarzni yaratish
            if self.salesman != shop_owner and not self.seller_debt:
                self.seller_debt = Debt.objects.create(
                    debt_type='accessory_seller',
                    creditor=shop_owner,
                    debtor_user=self.salesman,
                    debt_amount=self.debt_amount,
                    related_accessory_sale=self,
                    notes=f"Sotuvchi aksessuar qarzi: {self.accessory.name} ({self.quantity} dona)"
                )
                super().save(*args, **kwargs)
        else:
            # Qarzlarni o'chirish
            if self.customer_debt and self.customer_debt.paid_amount == 0:
                self.customer_debt.delete()
                self.customer_debt = None
            if self.seller_debt and self.seller_debt.paid_amount == 0:
                self.seller_debt.delete()
                self.seller_debt = None
            if not self.debt_amount:
                super().save(*args, **kwargs)


@receiver(pre_delete, sender=AccessorySale)
def return_accessory_quantity(sender, instance, **kwargs):
    accessory = instance.accessory
    accessory.quantity += instance.quantity
    accessory.save()


# Telefon almashtirish
class PhoneExchange(models.Model):
    new_phone = models.ForeignKey(Phone, on_delete=models.CASCADE, related_name="exchanges_as_new",
                                  verbose_name="Yangi telefon")
    old_phone_model = models.CharField(max_length=50, verbose_name="Eski telefon modeli")
    old_phone_memory = models.CharField(max_length=20, verbose_name="Eski telefon xotirasi")
    old_phone_value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Eski telefon qiymati")
    new_phone_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Yangi telefon narxi")
    price_difference = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Narx farqi")
    cash_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Naqd")
    card_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Karta")
    credit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Nasiya savdo")
    debt_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                      validators=[MaxValueValidator(500)], verbose_name="Qarz (max 500$)")
    salesman = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Sotuvchi")
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="phone_exchanges", verbose_name="Mijoz")
    customer_name = models.CharField(max_length=100, verbose_name="Mijoz ismi")
    customer_phone = models.CharField(max_length=15, verbose_name="Mijoz telefon raqami")
    customer_debt = models.OneToOneField(Debt, on_delete=models.SET_NULL, null=True, blank=True,
                                         related_name="customer_exchange", verbose_name="Mijoz qarzni")
    seller_debt = models.OneToOneField(Debt, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name="seller_exchange", verbose_name="Sotuvchi qarzni")
    notes = models.TextField(null=True, blank=True, verbose_name="Izoh")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="O'zgartirilgan sana")

    class Meta:
        verbose_name = "Telefon almashtirish"
        verbose_name_plural = "Telefon almashtirishlar"

    def __str__(self):
        return f"{self.customer_name} - {self.old_phone_model} → {self.new_phone}"

    def clean(self):
        # Narx farqini hisoblash
        calculated_difference = self.new_phone_price - self.old_phone_value
        if abs(self.price_difference - calculated_difference) > 0.01:
            self.price_difference = calculated_difference

        # To'lovlar yig'indisini tekshirish
        total_payments = self.cash_amount + self.card_amount + self.credit_amount + self.debt_amount
        if abs(total_payments - self.price_difference) > 0.01:
            raise ValidationError(
                f"To'lovlar yig'indisi ({total_payments}) narx farqiga ({self.price_difference}) teng bo'lishi kerak!"
            )

    def save(self, *args, **kwargs):
        # Validatsiya
        self.full_clean()

        # Telefon holatini o'zgartirish
        self.new_phone.status = 'sold'
        self.new_phone.save()

        # Mijozni yaratish yoki topish
        if not self.customer:
            try:
                existing_customer = Customer.objects.get(
                    phone_number=self.customer_phone,
                    shop=self.new_phone.shop
                )
                self.customer = existing_customer
            except Customer.DoesNotExist:
                self.customer = Customer.objects.create(
                    shop=self.new_phone.shop,
                    name=self.customer_name,
                    phone_number=self.customer_phone,
                    created_by=self.salesman
                )

        super().save(*args, **kwargs)

        # Qarzlarni boshqarish
        shop_owner = self.new_phone.shop.owner

        if self.debt_amount > 0:
            # Mijoz qarzni yaratish
            if not self.customer_debt:
                self.customer_debt = Debt.objects.create(
                    debt_type='phone_customer',
                    creditor=shop_owner,
                    customer=self.customer,
                    debt_amount=self.debt_amount,
                    notes=f"Mijoz almashtirish qarzi: {self.old_phone_model} → {self.new_phone}"
                )
                super().save(*args, **kwargs)

            # Sotuvchi qarzni yaratish
            if self.salesman != shop_owner and not self.seller_debt:
                self.seller_debt = Debt.objects.create(
                    debt_type='phone_seller',
                    creditor=shop_owner,
                    debtor_user=self.salesman,
                    debt_amount=self.debt_amount,
                    notes=f"Sotuvchi almashtirish qarzi: {self.old_phone_model} → {self.new_phone} (Mijoz: {self.customer_name})"
                )
                super().save(*args, **kwargs)


# Xarajatlar
class Expense(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="expenses", verbose_name="Do'kon")
    name = models.CharField(max_length=200, verbose_name="Xarajat nomi")
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)],
                                 verbose_name="Summa")
    expense_date = models.DateField(verbose_name="Xarajat sanasi")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name="Qo'shgan foydalanuvchi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")

    class Meta:
        verbose_name = "Xarajat"
        verbose_name_plural = "Xarajatlar"
        ordering = ['-expense_date', '-created_at']

    def __str__(self):
        return f"{self.name} - {self.amount:,.0f}$ ({self.expense_date})"


# Oylik hisobot
class MonthlyReport(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="monthly_reports", verbose_name="Do'kon")
    report_month = models.DateField(verbose_name="Hisobot oyi")  # Har oyning 1-sanasi

    # Telefon sotuvlari
    phones_sold_count = models.IntegerField(default=0, verbose_name="Sotilgan telefonlar soni")
    phones_sold_total_value = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                                  verbose_name="Telefonlar sotish summasi")
    phones_sold_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                             verbose_name="Telefonlardan foyda")

    # Aksessuar sotuvlari
    accessories_sold_count = models.IntegerField(default=0, verbose_name="Sotilgan aksessuarlar soni")
    accessories_sold_total_value = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                                       verbose_name="Aksessuarlar sotish summasi")
    accessories_sold_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                                  verbose_name="Aksessuarlardan foyda")

    # Almashtirishlar
    exchanges_count = models.IntegerField(default=0, verbose_name="Almashtirishlar soni")
    exchange_difference_total = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                                    verbose_name="Almashtirish farqi summasi")

    # Telefonlar xarid qilish
    phones_purchased_count = models.IntegerField(default=0, verbose_name="Xarid qilingan telefonlar")
    phones_purchased_total_value = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                                       verbose_name="Telefonlar xarid summasi")

    # To'lovlar
    cash_received = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                        verbose_name="Naqd olingan")
    card_received = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                        verbose_name="Karta orqali olingan")
    credit_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                        verbose_name="Nasiya savdolar")
    debt_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                      verbose_name="Qarz savdolar")

    # Xarajatlar
    total_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                         verbose_name="Umumiy xarajatlar")

    # Usta xizmatlari
    master_services_count = models.IntegerField(default=0, verbose_name="Usta xizmatlari soni")
    master_services_total = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                                verbose_name="Usta xizmatlari summasi")
    master_services_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                               verbose_name="Ustaga to'langan")

    # Qarzlar
    debts_given = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                      verbose_name="Berilgan qarzlar")
    debts_received = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                         verbose_name="Olingan qarz to'lovlari")

    # Umumiy natijalar
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                        verbose_name="Umumiy daromad")
    total_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                       verbose_name="Umumiy foyda")
    net_cash_flow = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                        verbose_name="Sof naqd oqimi")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")

    class Meta:
        verbose_name = "Oylik hisobot"
        verbose_name_plural = "Oylik hisobotlar"
        unique_together = ['shop', 'report_month']
        ordering = ['-report_month']

    def __str__(self):
        month_name = self.report_month.strftime('%Y/%m')
        return f"{self.shop.name} - {month_name} - Foyda: {self.total_profit:,.0f}$"

    def update_from_monthly_data(self):
        """Oylik ma'lumotlarni hisoblash"""
        from django.db.models import Sum, Count
        from datetime import datetime

        # Oy boshlanish va tugash sanalarini aniqlash
        year = self.report_month.year
        month = self.report_month.month
        start_date = datetime(year, month, 1).date()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).date()
        else:
            end_date = datetime(year, month + 1, 1).date()

        # Telefon sotuvlari
        phone_sales = PhoneSale.objects.filter(
            phone__shop=self.shop,
            created_at__date__gte=start_date,
            created_at__date__lt=end_date
        )
        self.phones_sold_count = phone_sales.count()
        self.phones_sold_total_value = phone_sales.aggregate(Sum('sale_price'))['sale_price__sum'] or 0
        self.phones_sold_profit = sum(sale.profit for sale in phone_sales)

        # Aksessuar sotuvlari
        accessory_sales = AccessorySale.objects.filter(
            accessory__shop=self.shop,
            created_at__date__gte=start_date,
            created_at__date__lt=end_date
        )
        self.accessories_sold_count = accessory_sales.count()
        self.accessories_sold_total_value = accessory_sales.aggregate(Sum('total_sale_price'))[
                                                'total_sale_price__sum'] or 0
        self.accessories_sold_profit = sum(sale.profit for sale in accessory_sales)

        # Almashtirishlar
        exchanges = PhoneExchange.objects.filter(
            new_phone__shop=self.shop,
            created_at__date__gte=start_date,
            created_at__date__lt=end_date
        )
        self.exchanges_count = exchanges.count()
        self.exchange_difference_total = exchanges.aggregate(Sum('price_difference'))['price_difference__sum'] or 0

        # Telefonlar xaridi
        purchased_phones = Phone.objects.filter(
            shop=self.shop,
            created_at__date__gte=start_date,
            created_at__date__lt=end_date,
            source_type__in=['client', 'daily_client', 'supplier']
        )
        self.phones_purchased_count = purchased_phones.count()
        self.phones_purchased_total_value = purchased_phones.aggregate(Sum('purchase_price'))[
                                                'purchase_price__sum'] or 0

        # To'lovlarni hisoblash
        phone_cash = phone_sales.aggregate(Sum('cash_amount'))['cash_amount__sum'] or 0
        phone_card = phone_sales.aggregate(Sum('card_amount'))['card_amount__sum'] or 0
        phone_credit = phone_sales.aggregate(Sum('credit_amount'))['credit_amount__sum'] or 0
        phone_debt = phone_sales.aggregate(Sum('debt_amount'))['debt_amount__sum'] or 0

        accessory_cash = accessory_sales.aggregate(Sum('cash_amount'))['cash_amount__sum'] or 0
        accessory_card = accessory_sales.aggregate(Sum('card_amount'))['card_amount__sum'] or 0
        accessory_debt = accessory_sales.aggregate(Sum('debt_amount'))['debt_amount__sum'] or 0

        exchange_cash = exchanges.aggregate(Sum('cash_amount'))['cash_amount__sum'] or 0
        exchange_card = exchanges.aggregate(Sum('card_amount'))['card_amount__sum'] or 0
        exchange_credit = exchanges.aggregate(Sum('credit_amount'))['credit_amount__sum'] or 0
        exchange_debt = exchanges.aggregate(Sum('debt_amount'))['debt_amount__sum'] or 0

        self.cash_received = phone_cash + accessory_cash + exchange_cash
        self.card_received = phone_card + accessory_card + exchange_card
        self.credit_amount = phone_credit + exchange_credit
        self.debt_amount = phone_debt + accessory_debt + exchange_debt

        # Xarajatlar
        expenses = Expense.objects.filter(
            shop=self.shop,
            expense_date__gte=start_date,
            expense_date__lt=end_date
        )
        self.total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0

        # Usta xizmatlari
        master_services = MasterService.objects.filter(
            phone__shop=self.shop,
            created_at__date__gte=start_date,
            created_at__date__lt=end_date
        )
        self.master_services_count = master_services.count()
        self.master_services_total = master_services.aggregate(Sum('service_fee'))['service_fee__sum'] or 0
        self.master_services_paid = master_services.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0

        # Qarzlar
        debts = Debt.objects.filter(
            creditor=self.shop.owner,
            created_at__date__gte=start_date,
            created_at__date__lt=end_date
        )
        self.debts_given = debts.aggregate(Sum('debt_amount'))['debt_amount__sum'] or 0

        debt_payments = DebtPayment.objects.filter(
            debt__creditor=self.shop.owner,
            payment_date__date__gte=start_date,
            payment_date__date__lt=end_date
        )
        self.debts_received = debt_payments.aggregate(Sum('payment_amount'))['payment_amount__sum'] or 0

        # Umumiy natijalar
        self.total_revenue = self.phones_sold_total_value + self.accessories_sold_total_value + self.exchange_difference_total
        self.total_profit = self.phones_sold_profit + self.accessories_sold_profit + self.exchange_difference_total
        self.net_cash_flow = self.cash_received + self.card_received - self.total_expenses - self.phones_purchased_total_value


# Kunlik hisobot
class DailyReport(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name="daily_reports", verbose_name="Do'kon")
    report_date = models.DateField(verbose_name="Hisobot sanasi")
    phones_sold_count = models.IntegerField(default=0, verbose_name="Sotilgan telefonlar soni")
    accessories_sold_count = models.IntegerField(default=0, verbose_name="Sotilgan aksessuarlar soni")
    exchanges_count = models.IntegerField(default=0, verbose_name="Almashtirishlar soni")
    phones_purchased_count = models.IntegerField(default=0, verbose_name="Hisoblab olingan telefonlar soni")
    phones_purchased_total_value = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                                       verbose_name="Hisoblab olingan telefonlar umumiy qiymati")
    phones_purchased_cash_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                                     verbose_name="Hisoblab olish uchun naqd to'langan")
    exchange_phones_accepted_count = models.IntegerField(default=0,
                                                         verbose_name="Almashtirishda qabul qilingan telefonlar soni")
    exchange_phones_accepted_value = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                                         verbose_name="Almashtirishda qabul qilingan telefonlar qiymati")
    exchange_new_phones_sold_value = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                                         verbose_name="Almashtirishda sotilgan yangi telefonlar qiymati")
    phone_sales_total = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                            verbose_name="Telefon sotuvlari umumiy summa")
    phone_sales_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                             verbose_name="Telefon sotuvlaridan foyda")
    accessory_sales_total = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                                verbose_name="Aksessuar sotuvlari umumiy summa")
    accessory_sales_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                                 verbose_name="Aksessuar sotuvlaridan foyda")
    exchange_difference_total = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                                    verbose_name="Almashtirishlardan farq summasi")
    total_expenses = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                         verbose_name="Umumiy xarajatlar")
    cash_received = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                        verbose_name="Naqd olingan")
    card_received = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                        verbose_name="Karta orqali olingan")
    credit_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                        verbose_name="Nasiya savdolar")
    debt_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                      verbose_name="Qarz savdolar")
    total_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                       verbose_name="Kunlik umumiy foyda")
    cash_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0,
                                       verbose_name="Kassadagi naqd")
    cash_calculation_display = models.CharField(max_length=500, blank=True,
                                                verbose_name="Kassa hisoblash ko'rinishi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")

    class Meta:
        verbose_name = "Kunlik hisobot"
        verbose_name_plural = "Kunlik hisobotlar"
        unique_together = ['shop', 'report_date']
        ordering = ['-report_date']

    def __str__(self):
        return f"{self.shop.name} - {self.report_date} - Kassada: {self.cash_balance:,.0f}$ - Foyda: {self.total_profit:,.0f}$"

    def calculate_cash_balance(self):
        self.cash_balance = self.cash_received - self.total_expenses - self.phones_purchased_cash_paid
        calculation_parts = [f"{self.cash_received:,.0f}$ (naqd kirim)"]
        if self.total_expenses > 0:
            calculation_parts.append(f"- {self.total_expenses:,.0f}$ (xarajatlar)")
        if self.phones_purchased_cash_paid > 0:
            calculation_parts.append(f"- {self.phones_purchased_cash_paid:,.0f}$ (hisoblab olish)")
        calculation_parts.append(f"= {self.cash_balance:,.0f}$")
        self.cash_calculation_display = " ".join(calculation_parts)

    def update_from_daily_data(self):
        from django.db.models import Sum, Count
        today = self.report_date

        # Telefon sotuvlari
        phone_sales = PhoneSale.objects.filter(phone__shop=self.shop, created_at__date=today)
        self.phones_sold_count = phone_sales.count()
        self.phone_sales_total = phone_sales.aggregate(Sum('sale_price'))['sale_price__sum'] or 0
        self.phone_sales_profit = sum(sale.profit for sale in phone_sales)

        # Aksessuar sotuvlari
        accessory_sales = AccessorySale.objects.filter(accessory__shop=self.shop, created_at__date=today)
        self.accessories_sold_count = accessory_sales.count()
        self.accessory_sales_total = accessory_sales.aggregate(Sum('total_sale_price'))['total_sale_price__sum'] or 0
        self.accessory_sales_profit = sum(sale.profit for sale in accessory_sales)

        # Almashtirishlar
        exchanges = PhoneExchange.objects.filter(new_phone__shop=self.shop, created_at__date=today)
        self.exchanges_count = exchanges.count()
        self.exchange_difference_total = exchanges.aggregate(Sum('price_difference'))['price_difference__sum'] or 0
        self.exchange_phones_accepted_count = exchanges.count()
        self.exchange_phones_accepted_value = exchanges.aggregate(Sum('old_phone_value'))['old_phone_value__sum'] or 0
        self.exchange_new_phones_sold_value = exchanges.aggregate(Sum('new_phone_price'))['new_phone_price__sum'] or 0

        # Telefon xaridlari
        purchased_phones = Phone.objects.filter(
            shop=self.shop, created_at__date=today, source_type__in=['client', 'daily_client'])
        self.phones_purchased_count = purchased_phones.count()
        self.phones_purchased_total_value = purchased_phones.aggregate(Sum('purchase_price'))[
                                                'purchase_price__sum'] or 0
        self.phones_purchased_cash_paid = self.phones_purchased_total_value

        # Xarajatlar
        expenses = Expense.objects.filter(shop=self.shop, expense_date=today)
        self.total_expenses = expenses.aggregate(Sum('amount'))['amount__sum'] or 0

        # To'lovlar
        phone_cash = phone_sales.aggregate(Sum('cash_amount'))['cash_amount__sum'] or 0
        phone_card = phone_sales.aggregate(Sum('card_amount'))['card_amount__sum'] or 0
        phone_credit = phone_sales.aggregate(Sum('credit_amount'))['credit_amount__sum'] or 0
        phone_debt = phone_sales.aggregate(Sum('debt_amount'))['debt_amount__sum'] or 0

        accessory_cash = accessory_sales.aggregate(Sum('cash_amount'))['cash_amount__sum'] or 0
        accessory_card = accessory_sales.aggregate(Sum('card_amount'))['card_amount__sum'] or 0
        accessory_debt = accessory_sales.aggregate(Sum('debt_amount'))['debt_amount__sum'] or 0

        exchange_cash = exchanges.aggregate(Sum('cash_amount'))['cash_amount__sum'] or 0
        exchange_card = exchanges.aggregate(Sum('card_amount'))['card_amount__sum'] or 0
        exchange_credit = exchanges.aggregate(Sum('credit_amount'))['credit_amount__sum'] or 0
        exchange_debt = exchanges.aggregate(Sum('debt_amount'))['debt_amount__sum'] or 0

        self.cash_received = phone_cash + accessory_cash + exchange_cash
        self.card_received = phone_card + accessory_card + exchange_card
        self.credit_amount = phone_credit + exchange_credit
        self.debt_amount = phone_debt + accessory_debt + exchange_debt

        # Umumiy foyda
        self.total_profit = self.phone_sales_profit + self.accessory_sales_profit + self.exchange_difference_total

        # Kassa hisobi
        self.calculate_cash_balance()

    def save(self, *args, **kwargs):
        self.update_from_daily_data()
        super().save(*args, **kwargs)


# SIGNALLARNI TO'G'IRLASH - BARCHA O'ZGARISHLARNI KUZATISH
def update_daily_and_monthly_reports(shop, date):
    """Kunlik va oylik hisobotlarni yangilash"""
    from django.core.exceptions import MultipleObjectsReturned

    # Kunlik hisobot
    try:
        daily_report, created = DailyReport.objects.get_or_create(
            shop=shop,
            report_date=date
        )
    except MultipleObjectsReturned:
        # Agar bir nechta yozuv topilsa, birinchisini olib, qolganlarini o'chiramiz
        daily_reports = DailyReport.objects.filter(
            shop=shop,
            report_date=date
        ).order_by('id')

        daily_report = daily_reports.first()
        # Qolgan duplikat yozuvlarni o'chirish
        daily_reports.exclude(id=daily_report.id).delete()
        created = False

    daily_report.update_from_daily_data()
    daily_report.save()

    # Oylik hisobot
    month_start = datetime(date.year, date.month, 1).date()
    try:
        monthly_report, created = MonthlyReport.objects.get_or_create(
            shop=shop,
            report_month=month_start
        )
    except MultipleObjectsReturned:
        # Agar bir nechta yozuv topilsa, birinchisini olib, qolganlarini o'chiramiz
        monthly_reports = MonthlyReport.objects.filter(
            shop=shop,
            report_month=month_start
        ).order_by('id')

        monthly_report = monthly_reports.first()
        # Qolgan duplikat yozuvlarni o'chirish
        monthly_reports.exclude(id=monthly_report.id).delete()
        created = False

    monthly_report.update_from_monthly_data()
    monthly_report.save()


# Telefon sotish signallari
@receiver(post_save, sender=PhoneSale)
def update_reports_on_phone_sale_save(sender, instance, created, **kwargs):
    update_daily_and_monthly_reports(instance.phone.shop, instance.created_at.date())


@receiver(pre_delete, sender=PhoneSale)
def update_reports_on_phone_sale_delete(sender, instance, **kwargs):
    # Pre-delete da saqlash kerak chunki post_delete da instance.phone mavjud bo'lmasligi mumkin
    shop = instance.phone.shop
    date = instance.created_at.date()
    # Delete dan keyin yangilash uchun
    from django.db import transaction
    transaction.on_commit(lambda: update_daily_and_monthly_reports(shop, date))


# Aksessuar sotish signallari
@receiver(post_save, sender=AccessorySale)
def update_reports_on_accessory_sale_save(sender, instance, created, **kwargs):
    update_daily_and_monthly_reports(instance.accessory.shop, instance.created_at.date())


@receiver(pre_delete, sender=AccessorySale)
def update_reports_on_accessory_sale_delete(sender, instance, **kwargs):
    shop = instance.accessory.shop
    date = instance.created_at.date()
    from django.db import transaction
    transaction.on_commit(lambda: update_daily_and_monthly_reports(shop, date))


# Telefon almashtirish signallari
@receiver(post_save, sender=PhoneExchange)
def update_reports_on_exchange_save(sender, instance, created, **kwargs):
    update_daily_and_monthly_reports(instance.new_phone.shop, instance.created_at.date())


@receiver(pre_delete, sender=PhoneExchange)
def update_reports_on_exchange_delete(sender, instance, **kwargs):
    shop = instance.new_phone.shop
    date = instance.created_at.date()
    from django.db import transaction
    transaction.on_commit(lambda: update_daily_and_monthly_reports(shop, date))


# Telefon xarid signallari
@receiver(post_save, sender=Phone)
def update_reports_on_phone_purchase_save(sender, instance, created, **kwargs):
    if instance.source_type in ['client', 'daily_client']:
        update_daily_and_monthly_reports(instance.shop, instance.created_at.date())


@receiver(pre_delete, sender=Phone)
def update_reports_on_phone_delete(sender, instance, **kwargs):
    if instance.source_type in ['client', 'daily_client']:
        shop = instance.shop
        date = instance.created_at.date()
        from django.db import transaction
        transaction.on_commit(lambda: update_daily_and_monthly_reports(shop, date))


# Xarajat signallari
@receiver(post_save, sender=Expense)
def update_reports_on_expense_save(sender, instance, created, **kwargs):
    update_daily_and_monthly_reports(instance.shop, instance.expense_date)


@receiver(pre_delete, sender=Expense)
def update_reports_on_expense_delete(sender, instance, **kwargs):
    shop = instance.shop
    date = instance.expense_date
    from django.db import transaction
    transaction.on_commit(lambda: update_daily_and_monthly_reports(shop, date))


# Usta xizmati signallari
@receiver(post_save, sender=MasterService)
def update_reports_on_master_service_save(sender, instance, created, **kwargs):
    update_daily_and_monthly_reports(instance.phone.shop, instance.created_at.date())


@receiver(pre_delete, sender=MasterService)
def update_reports_on_master_service_delete(sender, instance, **kwargs):
    shop = instance.phone.shop
    date = instance.created_at.date()
    from django.db import transaction
    transaction.on_commit(lambda: update_daily_and_monthly_reports(shop, date))


# Usta to'lovi signallari
@receiver(post_save, sender=MasterPayment)
def update_reports_on_master_payment_save(sender, instance, created, **kwargs):
    update_daily_and_monthly_reports(instance.master_service.phone.shop, instance.payment_date.date())


@receiver(pre_delete, sender=MasterPayment)
def update_reports_on_master_payment_delete(sender, instance, **kwargs):
    shop = instance.master_service.phone.shop
    date = instance.payment_date.date()
    from django.db import transaction
    transaction.on_commit(lambda: update_daily_and_monthly_reports(shop, date))


# Qarz to'lovi signallari
@receiver(post_save, sender=DebtPayment)
def update_reports_on_debt_payment_save(sender, instance, created, **kwargs):
    shop = None
    if hasattr(instance.debt, 'related_phone_sale') and instance.debt.related_phone_sale:
        shop = instance.debt.related_phone_sale.phone.shop
    elif hasattr(instance.debt, 'related_accessory_sale') and instance.debt.related_accessory_sale:
        shop = instance.debt.related_accessory_sale.accessory.shop
    elif hasattr(instance.debt, 'related_phone_exchange') and instance.debt.related_phone_exchange:
        shop = instance.debt.related_phone_exchange.new_phone.shop

    if shop:
        update_daily_and_monthly_reports(shop, instance.payment_date.date())


@receiver(pre_delete, sender=DebtPayment)
def update_reports_on_debt_payment_delete(sender, instance, **kwargs):
    shop = None
    if hasattr(instance.debt, 'related_phone_sale') and instance.debt.related_phone_sale:
        shop = instance.debt.related_phone_sale.phone.shop
    elif hasattr(instance.debt, 'related_accessory_sale') and instance.debt.related_accessory_sale:
        shop = instance.debt.related_accessory_sale.accessory.shop
    elif hasattr(instance.debt, 'related_phone_exchange') and instance.debt.related_phone_exchange:
        shop = instance.debt.related_phone_exchange.new_phone.shop

    if shop:
        date = instance.payment_date.date()
        from django.db import transaction
        transaction.on_commit(lambda: update_daily_and_monthly_reports(shop, date))