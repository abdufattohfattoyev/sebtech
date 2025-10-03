# sales/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum
from django.db import transaction
from decimal import Decimal
from .models import PhoneSale, PhoneExchange, Debt, DebtPayment, Expense, PhoneReturn, AccessorySale
from django.db import models

# ==================== PhoneSale Signals ====================

@receiver(post_save, sender=PhoneSale)
def handle_phone_sale_create_update(sender, instance, created, **kwargs):
    """PhoneSale yaratilganda yoki yangilanganda"""
    try:
        with transaction.atomic():
            if instance.phone:
                instance.phone.status = 'sold'
                instance.phone.save(update_fields=['status'])

    except Exception as e:
        print(f"PhoneSale signal error: {e}")


@receiver(post_delete, sender=PhoneSale)
def handle_phone_sale_delete(sender, instance, **kwargs):
    """PhoneSale o'chirilganda telefon va BARCHA bog'liq qarzlarni o'chirish"""
    try:
        with transaction.atomic():
            # 1️⃣ Telefonni 'shop' holatiga qaytarish
            if instance.phone:
                instance.phone.status = 'shop'
                instance.phone.save(update_fields=['status'])
                print(f"Telefon {instance.phone.imei} 'shop' holatiga qaytarildi")

            # 2️⃣ BARCHA BOG'LIQ QARZLARNI O'CHIRISH
            if instance.customer and instance.phone:
                # a) Mijoz → Sotuvchi qarz
                customer_debts_deleted = Debt.objects.filter(
                    debt_type='customer_to_seller',
                    customer=instance.customer,
                    creditor=instance.salesman,
                    currency='USD'
                ).filter(
                    models.Q(notes__icontains=instance.phone.imei) |
                    models.Q(notes__icontains=str(instance.phone.phone_model)) |
                    models.Q(notes__icontains=str(instance.id))
                ).delete()

                print(f"Mijoz → Sotuvchi qarzlar o'chirildi: {customer_debts_deleted[0]} ta")

                # b) Sotuvchi → Boss qarz
                shop_owner = instance.phone.shop.owner
                if shop_owner:
                    seller_debts_deleted = Debt.objects.filter(
                        debt_type='seller_to_boss',
                        debtor=instance.salesman,
                        creditor=shop_owner,
                        currency='USD'
                    ).filter(
                        models.Q(notes__icontains=instance.phone.imei) |
                        models.Q(notes__icontains=str(instance.phone.phone_model)) |
                        models.Q(notes__icontains=str(instance.customer.name))
                    ).delete()

                    print(f"Sotuvchi → Boss qarzlar o'chirildi: {seller_debts_deleted[0]} ta")

            print(f"PhoneSale #{instance.id} o'chirildi va barcha qarzlar tozalandi")

    except Exception as e:
        print(f"PhoneSale delete signal error: {e}")
        import traceback
        traceback.print_exc()


# ==================== PhoneExchange Signals ====================

@receiver(post_save, sender=PhoneExchange)
def handle_phone_exchange_create_update(sender, instance, created, **kwargs):
    """PhoneExchange yaratilganda yoki yangilanganda"""
    try:
        with transaction.atomic():
            if instance.new_phone:
                instance.new_phone.status = 'sold'
                instance.new_phone.save(update_fields=['status'])

            if instance.created_old_phone:
                instance.created_old_phone.status = 'shop'
                instance.created_old_phone.save(update_fields=['status'])

    except Exception as e:
        print(f"PhoneExchange signal error: {e}")


@receiver(post_delete, sender=PhoneExchange)
def handle_phone_exchange_delete(sender, instance, **kwargs):
    """PhoneExchange o'chirilganda"""
    try:
        with transaction.atomic():
            if instance.new_phone:
                instance.new_phone.status = 'shop'
                instance.new_phone.save(update_fields=['status'])

            if instance.created_old_phone:
                instance.created_old_phone.delete()

            if instance.debt_amount > 0 and instance.exchange_type == 'customer_pays':
                shop_owner = instance.new_phone.shop.owner if instance.new_phone else None

                if shop_owner:
                    Debt.objects.filter(
                        debt_type='customer_to_seller',
                        creditor=shop_owner,
                        customer=instance.customer,
                        currency='USD',
                        status='active',
                        notes__contains=instance.new_phone.imei
                    ).delete()

    except Exception as e:
        print(f"PhoneExchange delete signal error: {e}")


# ==================== Debt Signals ====================

@receiver(post_save, sender=Debt)
def handle_debt_create_update(sender, instance, created, **kwargs):
    """Debt yaratilganda yoki yangilanganda"""
    try:
        if created:
            print(f"Yangi qarz yaratildi: {instance.get_debt_type_display()}, {instance.debt_amount}")

    except Exception as e:
        print(f"Debt signal error: {e}")


@receiver(post_delete, sender=Debt)
def handle_debt_delete(sender, instance, **kwargs):
    """Debt o'chirilganda"""
    try:
        print(f"Qarz o'chirildi: {instance.get_debt_type_display()}, {instance.debt_amount}")

    except Exception as e:
        print(f"Debt delete signal error: {e}")


# ==================== DebtPayment Signals ====================

@receiver(post_save, sender=DebtPayment)
def handle_debt_payment_create_update(sender, instance, created, **kwargs):
    """DebtPayment yaratilganda yoki yangilanganda"""
    try:
        with transaction.atomic():
            debt = instance.debt
            if debt:
                total_paid = debt.payments.aggregate(total=Sum('payment_amount'))['total'] or Decimal('0')
                debt.paid_amount = total_paid

                if debt.paid_amount >= debt.debt_amount:
                    debt.status = 'paid'
                else:
                    debt.status = 'active'

                debt.save(update_fields=['paid_amount', 'status'])

    except Exception as e:
        print(f"DebtPayment signal error: {e}")


@receiver(post_delete, sender=DebtPayment)
def handle_debt_payment_delete(sender, instance, **kwargs):
    """DebtPayment o'chirilganda"""
    try:
        with transaction.atomic():
            debt = instance.debt
            if debt:
                total_paid = debt.payments.aggregate(total=Sum('payment_amount'))['total'] or Decimal('0')
                debt.paid_amount = total_paid

                if debt.paid_amount >= debt.debt_amount:
                    debt.status = 'paid'
                else:
                    debt.status = 'active'

                debt.save(update_fields=['paid_amount', 'status'])

    except Exception as e:
        print(f"DebtPayment delete signal error: {e}")


# ==================== PhoneReturn Signals ====================

@receiver(post_save, sender=PhoneReturn)
def handle_phone_return_create_update(sender, instance, created, **kwargs):
    """PhoneReturn yaratilganda yoki yangilanganda"""
    try:
        with transaction.atomic():
            if instance.phone_sale and instance.phone_sale.phone:
                instance.phone_sale.phone.status = 'returned'
                instance.phone_sale.phone.save(update_fields=['status'])

    except Exception as e:
        print(f"PhoneReturn signal error: {e}")


@receiver(post_delete, sender=PhoneReturn)
def handle_phone_return_delete(sender, instance, **kwargs):
    """PhoneReturn o'chirilganda"""
    try:
        with transaction.atomic():
            if instance.phone_sale and instance.phone_sale.phone:
                instance.phone_sale.phone.status = 'sold'
                instance.phone_sale.phone.save(update_fields=['status'])

    except Exception as e:
        print(f"PhoneReturn delete signal error: {e}")


# ==================== Expense Signals ====================

@receiver(post_save, sender=Expense)
def handle_expense_create_update(sender, instance, created, **kwargs):
    """Expense yaratilganda yoki yangilanganda"""
    try:
        if created:
            print(f"Yangi xarajat: {instance.name}, {instance.amount} so'm")

    except Exception as e:
        print(f"Expense signal error: {e}")


@receiver(post_delete, sender=Expense)
def handle_expense_delete(sender, instance, **kwargs):
    """Expense o'chirilganda"""
    try:
        print(f"Xarajat o'chirildi: {instance.name}, {instance.amount} so'm")

    except Exception as e:
        print(f"Expense delete signal error: {e}")


# sales/signals.py

@receiver(post_delete, sender=AccessorySale)
def handle_accessory_sale_delete(sender, instance, **kwargs):
    """AccessorySale o'chirilganda aksessuar sonini qaytarish"""
    try:
        with transaction.atomic():
            if instance.accessory:
                # Sotilgan miqdorni ombor qaytarish
                instance.accessory.quantity += instance.quantity
                instance.accessory.save(update_fields=['quantity'])

            # Qarzni o'chirish
            if instance.debt_amount > 0:
                shop_owner = instance.accessory.shop.owner if instance.accessory else None

                if shop_owner:
                    Debt.objects.filter(
                        debt_type='customer_to_seller',
                        creditor=shop_owner,
                        customer=instance.customer,
                        currency='UZS',
                        status='active',
                        notes__contains=f"{instance.accessory.name}"
                    ).delete()

    except Exception as e:
        print(f"AccessorySale delete signal error: {e}")