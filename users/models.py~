from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal


class CommissionHistory(models.Model):
    """Komissiya foizlarining tarixi"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='commission_history')

    # Foizlar
    phone_commission_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Telefon komissiya (%)"
    )
    accessory_commission_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Aksessuar komissiya (%)"
    )
    exchange_commission_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Almashtirish komissiya (%)"
    )

    # Maoshlar
    base_salary_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Asosiy maosh (USD)"
    )
    base_salary_uzs = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Asosiy maosh (UZS)"
    )

    # Qachondan boshlab amal qiladi
    effective_date = models.DateField(
        verbose_name="Amal qilish sanasi",
        db_index=True
    )

    # Kim o'zgartirgan
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commission_changes',
        verbose_name="O'zgartirgan"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, verbose_name="Izoh")

    class Meta:
        ordering = ['-effective_date']
        indexes = [
            models.Index(fields=['user', 'effective_date']),
        ]
        verbose_name = "Komissiya tarixi"
        verbose_name_plural = "Komissiya tarixlari"

    def __str__(self):
        return f"{self.user.username} - {self.effective_date} dan"


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('boss', 'Rahbar'),
        ('finance', 'Moliyachi'),
        ('seller', 'Sotuvchi'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="Foydalanuvchi")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='seller', verbose_name="Rol")
    phone_number = models.CharField(max_length=15, null=True, blank=True, verbose_name="Telefon")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Rasm")

    # Komissiya foizlari (hozirgi)
    phone_commission_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('5.00'),
        verbose_name="Telefon komissiyasi (%)",
        help_text="Telefon foydasi foizi (Dollar)"
    )
    accessory_commission_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('10.00'),
        verbose_name="Aksessuar komissiyasi (%)",
        help_text="Aksessuar foydasi foizi (So'm)"
    )
    exchange_commission_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('5.00'),
        verbose_name="Almashtirish komissiyasi (%)",
        help_text="Almashtirish foydasi foizi (Dollar)"
    )

    # Asosiy maosh (hozirgi)
    base_salary_usd = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        verbose_name="Asosiy maosh (USD)",
        help_text="Dollar hisobida"
    )
    base_salary_uzs = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal('0.00'),
        verbose_name="Asosiy maosh (UZS)",
        help_text="So'm hisobida"
    )

    created_at = models.DateField(default=timezone.now, verbose_name="Yaratilgan")

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"

    def get_commission_rates_for_date(self, target_date):
        """
        Ma'lum sana uchun komissiya foizlarini olish

        Args:
            target_date: date object

        Returns:
            dict: Foizlar va maoshlar
        """
        history = CommissionHistory.objects.filter(
            user=self.user,
            effective_date__lte=target_date
        ).order_by('-effective_date').first()

        if history:
            return {
                'phone_rate': history.phone_commission_percent,
                'accessory_rate': history.accessory_commission_percent,
                'exchange_rate': history.exchange_commission_percent,
                'base_salary_usd': history.base_salary_usd,
                'base_salary_uzs': history.base_salary_uzs,
            }

        # Agar tarix bo'lmasa, hozirgi qiymatlarni qaytarish
        return {
            'phone_rate': self.phone_commission_percent,
            'accessory_rate': self.accessory_commission_percent,
            'exchange_rate': self.exchange_commission_percent,
            'base_salary_usd': self.base_salary_usd,
            'base_salary_uzs': self.base_salary_uzs,
        }

    def calculate_commission(self, phone_profit_usd=0, accessory_profit_uzs=0, exchange_profit_usd=0):
        """
        Komissiya hisoblash - hozirgi foizlar bilan

        Args:
            phone_profit_usd: Telefon foydasi (Dollar)
            accessory_profit_uzs: Aksessuar foydasi (So'm)
            exchange_profit_usd: Almashtirish foydasi (Dollar)

        Returns:
            dict: Komissiya tafsilotlari
        """
        # Decimal konvertatsiya
        phone_profit_usd = Decimal(str(phone_profit_usd)) if phone_profit_usd else Decimal('0')
        accessory_profit_uzs = Decimal(str(accessory_profit_uzs)) if accessory_profit_uzs else Decimal('0')
        exchange_profit_usd = Decimal(str(exchange_profit_usd)) if exchange_profit_usd else Decimal('0')

        # Komissiya hisoblash (har biri o'z valyutasida)
        phone_commission_usd = (phone_profit_usd * self.phone_commission_percent / 100).quantize(Decimal('0.01'))
        accessory_commission_uzs = (accessory_profit_uzs * self.accessory_commission_percent / 100).quantize(
            Decimal('0.01'))
        exchange_commission_usd = (exchange_profit_usd * self.exchange_commission_percent / 100).quantize(
            Decimal('0.01'))

        # Umumiy komissiya (valyutalar alohida)
        total_commission_usd = phone_commission_usd + exchange_commission_usd
        total_commission_uzs = accessory_commission_uzs

        # Umumiy maosh (valyutalar alohida)
        total_salary_usd = self.base_salary_usd + total_commission_usd
        total_salary_uzs = self.base_salary_uzs + total_commission_uzs

        return {
            # USD komissiyalari
            'phone_commission_usd': phone_commission_usd,
            'exchange_commission_usd': exchange_commission_usd,
            'total_commission_usd': total_commission_usd,

            # UZS komissiyalari
            'accessory_commission_uzs': accessory_commission_uzs,
            'total_commission_uzs': total_commission_uzs,

            # Asosiy maoshlar
            'base_salary_usd': self.base_salary_usd,
            'base_salary_uzs': self.base_salary_uzs,

            # Umumiy maoshlar
            'total_salary_usd': total_salary_usd,
            'total_salary_uzs': total_salary_uzs,

            # Foydalar
            'profits': {
                'phone_profit_usd': phone_profit_usd,
                'accessory_profit_uzs': accessory_profit_uzs,
                'exchange_profit_usd': exchange_profit_usd,
                'total_profit_usd': phone_profit_usd + exchange_profit_usd,
                'total_profit_uzs': accessory_profit_uzs,
            },

            # Komissiya foizlari
            'rates': {
                'phone_rate': self.phone_commission_percent,
                'accessory_rate': self.accessory_commission_percent,
                'exchange_rate': self.exchange_commission_percent,
            }
        }

    def save(self, *args, **kwargs):
        """Saqlashda tarix yaratish"""
        is_new = not self.pk

        if not is_new:
            # Eski qiymatlarni olish
            try:
                old_profile = UserProfile.objects.get(pk=self.pk)

                # Foizlar o'zgarganligi tekshirish
                if (old_profile.phone_commission_percent != self.phone_commission_percent or
                        old_profile.accessory_commission_percent != self.accessory_commission_percent or
                        old_profile.exchange_commission_percent != self.exchange_commission_percent or
                        old_profile.base_salary_usd != self.base_salary_usd or
                        old_profile.base_salary_uzs != self.base_salary_uzs):
                    # Yangi tarix yaratish
                    CommissionHistory.objects.create(
                        user=self.user,
                        phone_commission_percent=self.phone_commission_percent,
                        accessory_commission_percent=self.accessory_commission_percent,
                        exchange_commission_percent=self.exchange_commission_percent,
                        base_salary_usd=self.base_salary_usd,
                        base_salary_uzs=self.base_salary_uzs,
                        effective_date=timezone.now().date(),
                        notes="Avtomatik yaratildi (o'zgartirish)"
                    )
            except UserProfile.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        # Yangi profil uchun tarix yaratish
        if is_new:
            CommissionHistory.objects.create(
                user=self.user,
                phone_commission_percent=self.phone_commission_percent,
                accessory_commission_percent=self.accessory_commission_percent,
                exchange_commission_percent=self.exchange_commission_percent,
                base_salary_usd=self.base_salary_usd,
                base_salary_uzs=self.base_salary_uzs,
                effective_date=self.created_at,
                notes="Dastlabki yaratilish"
            )


# Signal: User yaratilganda avtomatik UserProfile yaratish
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """User yaratilganda UserProfile yaratish"""
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """User saqlanayotganda UserProfile ni ham saqlash"""
    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()