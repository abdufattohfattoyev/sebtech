
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from services.models import MasterService


@receiver(post_save, sender=MasterService)
def update_service_phone_status(sender, instance, created, **kwargs):
    """Xizmat saqlanganda telefon holatini yangilash"""
    if created:
        instance.update_phone_status()


@receiver(post_delete, sender=MasterService)
def restore_phone_status(sender, instance, **kwargs):
    """Xizmat o'chirilganda telefon holatini qaytarish"""
    if instance.phone:
        instance.phone.status = 'shop'
        instance.phone.save(update_fields=['status'])