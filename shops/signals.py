from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Customer
from sales.models import PhoneSale, AccessorySale, PhoneExchange, Debt, DebtPayment

@receiver(post_save, sender=PhoneSale)
def update_customer_on_phone_sale(sender, instance, created, **kwargs):
    """Telefon sotilganda mijozning umumiy xaridlarini yangilaydi."""
    if instance.customer:
        instance.customer.save()

@receiver(post_save, sender=AccessorySale)
def update_customer_on_accessory_sale(sender, instance, created, **kwargs):
    """Aksessuar sotilganda mijozning umumiy xaridlarini yangilaydi."""
    if instance.customer:
        instance.customer.save()

@receiver(post_save, sender=PhoneExchange)
def update_customer_on_phone_exchange(sender, instance, created, **kwargs):
    """Telefon almashtirilganda mijozning umumiy xaridlarini yangilaydi."""
    if instance.customer:
        instance.customer.save()

@receiver(post_save, sender=Debt)
def update_customer_on_debt(sender, instance, created, **kwargs):
    """Qarz yaratilganda mijozning umumiy qarzini yangilaydi."""
    if instance.customer:
        instance.customer.save()

@receiver(post_save, sender=DebtPayment)
def update_customer_on_debt_payment(sender, instance, created, **kwargs):
    """Qarz to'lovi qilinganda mijozning umumiy qarzini yangilaydi."""
    if instance.debt.customer:
        instance.debt.customer.save()