# sales/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum, Q
from django.db import transaction
from decimal import Decimal
from .models import PhoneSale, PhoneExchange, Debt, DebtPayment, Expense, PhoneReturn, AccessorySale
import logging

logger = logging.getLogger(__name__)


# ============ HELPER FUNCTIONS ============
def delete_related_debts(model_name, instance, currency, identifier_field):
    """Universal qarz o'chirish funksiyasi"""
    try:
        if not instance.customer or not hasattr(instance, identifier_field):
            return

        identifier = getattr(instance, identifier_field, '')
        if not identifier:
            return

        shop_owner = None
        if hasattr(instance, 'phone') and instance.phone:
            shop_owner = instance.phone.shop.owner
        elif hasattr(instance, 'accessory') and instance.accessory:
            shop_owner = instance.accessory.shop.owner
        elif hasattr(instance, 'new_phone') and instance.new_phone:
            shop_owner = instance.new_phone.shop.owner

        # Mijoz → Sotuvchi qarz
        customer_debts = Debt.objects.filter(
            debt_type='customer_to_seller',
            customer=instance.customer,
            currency=currency
        ).filter(
            Q(notes__icontains=str(identifier)) |
            Q(notes__icontains=instance.customer.name)
        )
        deleted_count = customer_debts.delete()[0]
        logger.info(f"{model_name} - Mijoz qarzlar o'chirildi: {deleted_count} ta")

        # Sotuvchi → Boss qarz
        if shop_owner and hasattr(instance, 'salesman'):
            seller_debts = Debt.objects.filter(
                debt_type='seller_to_boss',
                debtor=instance.salesman,
                creditor=shop_owner,
                currency=currency
            ).filter(
                Q(notes__icontains=str(identifier)) |
                Q(notes__icontains=instance.customer.name)
            )
            deleted_count = seller_debts.delete()[0]
            logger.info(f"{model_name} - Sotuvchi qarzlar o'chirildi: {deleted_count} ta")

    except Exception as e:
        logger.error(f"{model_name} delete_related_debts error: {e}", exc_info=True)


def update_phone_status(phone, status):
    """Telefon statusini yangilash"""
    if phone:
        phone.status = status
        phone.save(update_fields=['status'])


def update_debt_paid_amount(debt):
    """Qarz to'lovlarini yangilash"""
    try:
        total_paid = debt.payments.aggregate(total=Sum('payment_amount'))['total'] or Decimal('0')
        debt.paid_amount = total_paid
        debt.status = 'paid' if debt.paid_amount >= debt.debt_amount else 'active'
        debt.save(update_fields=['paid_amount', 'status'])
    except Exception as e:
        logger.error(f"update_debt_paid_amount error: {e}", exc_info=True)


# ============ PHONE SALE SIGNALS ============
@receiver(post_save, sender=PhoneSale)
def handle_phone_sale_save(sender, instance, created, **kwargs):
    """PhoneSale yaratilganda yoki yangilanganda"""
    try:
        with transaction.atomic():
            update_phone_status(instance.phone, 'sold')
    except Exception as e:
        logger.error(f"PhoneSale save signal error: {e}", exc_info=True)


@receiver(post_delete, sender=PhoneSale)
def handle_phone_sale_delete(sender, instance, **kwargs):
    """PhoneSale o'chirilganda - telefon va qarzlarni tozalash"""
    try:
        with transaction.atomic():
            # Telefonni qaytarish
            update_phone_status(instance.phone, 'shop')

            # Qarzlarni o'chirish
            if instance.phone:
                delete_related_debts('PhoneSale', instance, 'USD', 'phone')

            logger.info(f"PhoneSale #{instance.id} va barcha bog'liq qarzlar o'chirildi")
    except Exception as e:
        logger.error(f"PhoneSale delete signal error: {e}", exc_info=True)


# ============ ACCESSORY SALE SIGNALS ============
@receiver(post_delete, sender=AccessorySale)
def handle_accessory_sale_delete(sender, instance, **kwargs):
    """AccessorySale o'chirilganda - aksessuar va qarzlarni tozalash"""
    try:
        with transaction.atomic():
            # Aksessuar sonini qaytarish
            if instance.accessory:
                instance.accessory.quantity += instance.quantity
                instance.accessory.save(update_fields=['quantity'])

            # Qarzlarni o'chirish
            delete_related_debts('AccessorySale', instance, 'UZS', 'accessory')

            logger.info(f"AccessorySale #{instance.id} va barcha bog'liq qarzlar o'chirildi")
    except Exception as e:
        logger.error(f"AccessorySale delete signal error: {e}", exc_info=True)


# ============ PHONE EXCHANGE SIGNALS ============
@receiver(post_save, sender=PhoneExchange)
def handle_phone_exchange_save(sender, instance, created, **kwargs):
    """PhoneExchange yaratilganda yoki yangilanganda"""
    try:
        with transaction.atomic():
            update_phone_status(instance.new_phone, 'sold')
            update_phone_status(instance.created_old_phone, 'shop')
    except Exception as e:
        logger.error(f"PhoneExchange save signal error: {e}", exc_info=True)


@receiver(post_delete, sender=PhoneExchange)
def handle_phone_exchange_delete(sender, instance, **kwargs):
    """PhoneExchange o'chirilganda"""
    try:
        with transaction.atomic():
            # Yangi telefonni qaytarish
            update_phone_status(instance.new_phone, 'shop')

            # Eski yaratilgan telefonni o'chirish
            if instance.created_old_phone:
                instance.created_old_phone.delete()

            # Qarzlarni o'chirish
            if instance.exchange_type == 'customer_pays':
                delete_related_debts('PhoneExchange', instance, 'USD', 'new_phone')

            logger.info(f"PhoneExchange #{instance.id} va barcha bog'liq qarzlar o'chirildi")
    except Exception as e:
        logger.error(f"PhoneExchange delete signal error: {e}", exc_info=True)


# ============ DEBT PAYMENT SIGNALS ============
@receiver(post_save, sender=DebtPayment)
def handle_debt_payment_save(sender, instance, created, **kwargs):
    """DebtPayment yaratilganda yoki yangilanganda"""
    try:
        with transaction.atomic():
            update_debt_paid_amount(instance.debt)
            if created:
                logger.info(f"Yangi to'lov: {instance.payment_amount} {instance.debt.currency_symbol}")
    except Exception as e:
        logger.error(f"DebtPayment save signal error: {e}", exc_info=True)


@receiver(post_delete, sender=DebtPayment)
def handle_debt_payment_delete(sender, instance, **kwargs):
    """DebtPayment o'chirilganda"""
    try:
        with transaction.atomic():
            update_debt_paid_amount(instance.debt)
            logger.info(f"To'lov o'chirildi: {instance.payment_amount} {instance.debt.currency_symbol}")
    except Exception as e:
        logger.error(f"DebtPayment delete signal error: {e}", exc_info=True)


# ============ PHONE RETURN SIGNALS ============
@receiver(post_save, sender=PhoneReturn)
def handle_phone_return_save(sender, instance, created, **kwargs):
    """PhoneReturn yaratilganda yoki yangilanganda"""
    try:
        with transaction.atomic():
            if instance.phone_sale and instance.phone_sale.phone:
                update_phone_status(instance.phone_sale.phone, 'returned')
                if created:
                    logger.info(f"Telefon qaytarildi: {instance.phone_sale.phone.imei}")
    except Exception as e:
        logger.error(f"PhoneReturn save signal error: {e}", exc_info=True)


@receiver(post_delete, sender=PhoneReturn)
def handle_phone_return_delete(sender, instance, **kwargs):
    """PhoneReturn o'chirilganda"""
    try:
        with transaction.atomic():
            if instance.phone_sale and instance.phone_sale.phone:
                update_phone_status(instance.phone_sale.phone, 'sold')
                logger.info(f"Telefon qaytarish bekor qilindi: {instance.phone_sale.phone.imei}")
    except Exception as e:
        logger.error(f"PhoneReturn delete signal error: {e}", exc_info=True)


# ============ LOGGING SIGNALS ============
@receiver(post_save, sender=Debt)
def handle_debt_save(sender, instance, created, **kwargs):
    """Debt yaratilganda log"""
    if created:
        logger.info(f"Yangi qarz: {instance.get_debt_type_display()}, {instance.debt_amount}{instance.currency_symbol}")


@receiver(post_delete, sender=Debt)
def handle_debt_delete(sender, instance, **kwargs):
    """Debt o'chirilganda log"""
    logger.info(
        f"Qarz o'chirildi: {instance.get_debt_type_display()}, {instance.debt_amount}{instance.currency_symbol}")


@receiver(post_save, sender=Expense)
def handle_expense_save(sender, instance, created, **kwargs):
    """Expense yaratilganda log"""
    if created:
        logger.info(f"Yangi xarajat: {instance.name}, {instance.amount:,.0f} so'm")


@receiver(post_delete, sender=Expense)
def handle_expense_delete(sender, instance, **kwargs):
    """Expense o'chirilganda log"""
    logger.info(f"Xarajat o'chirildi: {instance.name}, {instance.amount:,.0f} so'm")