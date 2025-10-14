# inventory/signals.py
from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Phone
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Phone)
def sync_phone_imei_to_exchange(sender, instance, **kwargs):
    """
    ✅ Agar Phone modelida IMEI o'zgartirilsa,
    PhoneExchange da ham yangilansin (ikki tomonlama sinxronizatsiya)
    """
    if not instance.pk:
        return  # Yangi telefon - signal ishlamaydi

    try:
        # Eski qiymatni olish
        old_phone = Phone.objects.get(pk=instance.pk)
        old_imei = old_phone.imei
        new_imei = instance.imei

        # IMEI o'zgarganligi tekshirish
        if old_imei != new_imei:
            logger.info(f"📱 Phone #{instance.pk} IMEI o'zgartirildi: {old_imei} → {new_imei}")

            # ✅ Agar bu telefon almashtirish orqali yaratilgan bo'lsa
            if hasattr(instance, 'created_from_exchange') and instance.created_from_exchange:
                from sales.models import PhoneExchange

                exchange = instance.created_from_exchange
                logger.info(f"🔄 PhoneExchange #{exchange.pk} da IMEI yangilanadi")

                # ✅ Signal chaqirilmasligi uchun update ishlatamiz
                PhoneExchange.objects.filter(pk=exchange.pk).update(old_phone_imei=new_imei)
                logger.info(f"✅ PhoneExchange #{exchange.pk} da IMEI yangilandi!")

    except Phone.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"❌ sync_phone_imei_to_exchange error: {e}", exc_info=True)