# reports/signals.py - TO'LIQ UPDATE QOBILIYATI

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from decimal import Decimal
from .models import CashFlowTransaction
from datetime import date


# ==================== TELEFON SOTISH ====================

@receiver(post_save, sender='sales.PhoneSale')
def handle_phone_sale_cashflow(sender, instance, created, **kwargs):
    """Telefon sotish - CREATE va UPDATE"""
    if instance.cash_amount <= 0:
        # Agar cash yo'q bo'lsa, mavjud cashflow ni o'chirish
        CashFlowTransaction.objects.filter(related_phone_sale=instance).delete()
        return

    try:
        if created:
            # Yangi sotish
            CashFlowTransaction.objects.create(
                shop=instance.phone.shop,
                transaction_date=instance.sale_date,
                transaction_type='phone_sale',
                amount_usd=instance.cash_amount,
                amount_uzs=Decimal('0'),
                related_phone=instance.phone,
                related_phone_sale=instance,
                description=f"Telefon: {instance.phone.phone_model} {instance.phone.memory_size}",
                notes=f"Mijoz: {instance.customer.name}",
                created_by=instance.salesman
            )
        else:
            # Yangilanish
            cashflow = CashFlowTransaction.objects.filter(related_phone_sale=instance).first()
            if cashflow:
                cashflow.transaction_date = instance.sale_date
                cashflow.amount_usd = instance.cash_amount
                cashflow.description = f"Telefon: {instance.phone.phone_model} {instance.phone.memory_size}"
                cashflow.notes = f"Mijoz: {instance.customer.name}"
                cashflow.save()
            else:
                # Agar cashflow topilmasa, yaratish
                CashFlowTransaction.objects.create(
                    shop=instance.phone.shop,
                    transaction_date=instance.sale_date,
                    transaction_type='phone_sale',
                    amount_usd=instance.cash_amount,
                    amount_uzs=Decimal('0'),
                    related_phone=instance.phone,
                    related_phone_sale=instance,
                    description=f"Telefon: {instance.phone.phone_model} {instance.phone.memory_size}",
                    notes=f"Mijoz: {instance.customer.name}",
                    created_by=instance.salesman
                )
    except Exception as e:
        print(f"❌ PhoneSale cashflow error: {e}")


@receiver(pre_delete, sender='sales.PhoneSale')
def delete_phone_sale_cashflow(sender, instance, **kwargs):
    try:
        CashFlowTransaction.objects.filter(related_phone_sale=instance).delete()
    except Exception as e:
        print(f"❌ PhoneSale delete error: {e}")


# ==================== AKSESSUAR SOTISH ====================

@receiver(post_save, sender='sales.AccessorySale')
def handle_accessory_sale_cashflow(sender, instance, created, **kwargs):
    """Aksessuar sotish - CREATE va UPDATE"""
    if instance.cash_amount <= 0:
        CashFlowTransaction.objects.filter(related_accessory_sale=instance).delete()
        return

    try:
        if created:
            CashFlowTransaction.objects.create(
                shop=instance.accessory.shop,
                transaction_date=instance.sale_date,
                transaction_type='accessory_sale',
                amount_uzs=instance.cash_amount,
                amount_usd=Decimal('0'),
                related_accessory_sale=instance,
                description=f"Aksessuar: {instance.accessory.name} x{instance.quantity}",
                notes=f"Mijoz: {instance.customer.name}",
                created_by=instance.salesman
            )
        else:
            cashflow = CashFlowTransaction.objects.filter(related_accessory_sale=instance).first()
            if cashflow:
                cashflow.transaction_date = instance.sale_date
                cashflow.amount_uzs = instance.cash_amount
                cashflow.description = f"Aksessuar: {instance.accessory.name} x{instance.quantity}"
                cashflow.notes = f"Mijoz: {instance.customer.name}"
                cashflow.save()
            else:
                CashFlowTransaction.objects.create(
                    shop=instance.accessory.shop,
                    transaction_date=instance.sale_date,
                    transaction_type='accessory_sale',
                    amount_uzs=instance.cash_amount,
                    amount_usd=Decimal('0'),
                    related_accessory_sale=instance,
                    description=f"Aksessuar: {instance.accessory.name} x{instance.quantity}",
                    notes=f"Mijoz: {instance.customer.name}",
                    created_by=instance.salesman
                )
    except Exception as e:
        print(f"❌ AccessorySale cashflow error: {e}")


@receiver(pre_delete, sender='sales.AccessorySale')
def delete_accessory_sale_cashflow(sender, instance, **kwargs):
    try:
        CashFlowTransaction.objects.filter(related_accessory_sale=instance).delete()
    except Exception as e:
        print(f"❌ AccessorySale delete error: {e}")

# ==================== ALMASHTIRISH ====================

@receiver(post_save, sender='sales.PhoneExchange')
def handle_exchange_cashflow(sender, instance, created, **kwargs):
    """Almashtirish - CREATE va UPDATE"""
    try:
        if created:
            # ========== YANGI ALMASHTIRISH ==========

            # 1️⃣ OLINGAN ESKI TELEFON QIYMATI - CHIQIM
            if instance.old_phone_accepted_price > 0:
                CashFlowTransaction.objects.create(
                    shop=instance.new_phone.shop,
                    transaction_date=instance.exchange_date,
                    transaction_type='exchange_old_phone_value',
                    amount_usd=-instance.old_phone_accepted_price,
                    amount_uzs=Decimal('0'),
                    related_phone=instance.new_phone,
                    related_exchange=instance,
                    description=f"Olingan telefon: {instance.old_phone_model}",
                    notes=f"Mijoz: {instance.customer_name} | Yangi: {instance.new_phone.phone_model}",
                    created_by=instance.salesman
                )

            # 2️⃣ MIJOZ TO'LAGAN FARQ
            if instance.exchange_type == 'customer_pays' and instance.cash_amount > 0:
                CashFlowTransaction.objects.create(
                    shop=instance.new_phone.shop,
                    transaction_date=instance.exchange_date,
                    transaction_type='exchange_income',
                    amount_usd=instance.cash_amount,
                    amount_uzs=Decimal('0'),
                    related_phone=instance.new_phone,
                    related_exchange=instance,
                    description=f"Mijoz to'lovi: {instance.old_phone_model} → {instance.new_phone.phone_model}",
                    notes=f"Mijoz: {instance.customer_name}",
                    created_by=instance.salesman
                )

            # 3️⃣ DO'KON TO'LAGAN FARQ
            elif instance.exchange_type == 'seller_pays' and instance.cash_amount > 0:
                CashFlowTransaction.objects.create(
                    shop=instance.new_phone.shop,
                    transaction_date=instance.exchange_date,
                    transaction_type='exchange_expense',
                    amount_usd=-instance.cash_amount,
                    amount_uzs=Decimal('0'),
                    related_phone=instance.new_phone,
                    related_exchange=instance,
                    description=f"Do'kon to'lovi: {instance.old_phone_model} → {instance.new_phone.phone_model}",
                    notes=f"Mijoz: {instance.customer_name}",
                    created_by=instance.salesman
                )

            # 4️⃣ TENG ALMASHTIRISH
            elif instance.exchange_type == 'equal':
                CashFlowTransaction.objects.create(
                    shop=instance.new_phone.shop,
                    transaction_date=instance.exchange_date,
                    transaction_type='exchange_equal',
                    amount_usd=Decimal('0'),
                    amount_uzs=Decimal('0'),
                    related_phone=instance.new_phone,
                    related_exchange=instance,
                    description=f"Teng: {instance.old_phone_model} = {instance.new_phone.phone_model}",
                    notes=f"Mijoz: {instance.customer_name}",
                    created_by=instance.salesman
                )

        else:
            # ========== YANGILANISH ==========
            CashFlowTransaction.objects.filter(related_exchange=instance).delete()

            # Qayta yaratish
            if instance.old_phone_accepted_price > 0:
                CashFlowTransaction.objects.create(
                    shop=instance.new_phone.shop,
                    transaction_date=instance.exchange_date,
                    transaction_type='exchange_old_phone_value',
                    amount_usd=-instance.old_phone_accepted_price,
                    amount_uzs=Decimal('0'),
                    related_phone=instance.new_phone,
                    related_exchange=instance,
                    description=f"Olingan telefon: {instance.old_phone_model}",
                    notes=f"Mijoz: {instance.customer_name} | Yangi: {instance.new_phone.phone_model}",
                    created_by=instance.salesman
                )

            if instance.exchange_type == 'customer_pays' and instance.cash_amount > 0:
                CashFlowTransaction.objects.create(
                    shop=instance.new_phone.shop,
                    transaction_date=instance.exchange_date,
                    transaction_type='exchange_income',
                    amount_usd=instance.cash_amount,
                    amount_uzs=Decimal('0'),
                    related_phone=instance.new_phone,
                    related_exchange=instance,
                    description=f"Mijoz to'lovi: {instance.old_phone_model} → {instance.new_phone.phone_model}",
                    notes=f"Mijoz: {instance.customer_name}",
                    created_by=instance.salesman
                )
            elif instance.exchange_type == 'seller_pays' and instance.cash_amount > 0:
                CashFlowTransaction.objects.create(
                    shop=instance.new_phone.shop,
                    transaction_date=instance.exchange_date,
                    transaction_type='exchange_expense',
                    amount_usd=-instance.cash_amount,
                    amount_uzs=Decimal('0'),
                    related_phone=instance.new_phone,
                    related_exchange=instance,
                    description=f"Do'kon to'lovi: {instance.old_phone_model} → {instance.new_phone.phone_model}",
                    notes=f"Mijoz: {instance.customer_name}",
                    created_by=instance.salesman
                )
            elif instance.exchange_type == 'equal':
                CashFlowTransaction.objects.create(
                    shop=instance.new_phone.shop,
                    transaction_date=instance.exchange_date,
                    transaction_type='exchange_equal',
                    amount_usd=Decimal('0'),
                    amount_uzs=Decimal('0'),
                    related_phone=instance.new_phone,
                    related_exchange=instance,
                    description=f"Teng: {instance.old_phone_model} = {instance.new_phone.phone_model}",
                    notes=f"Mijoz: {instance.customer_name}",
                    created_by=instance.salesman
                )

    except Exception as e:
        print(f"❌ Exchange cashflow error: {e}")


@receiver(pre_delete, sender='sales.PhoneExchange')
def delete_exchange_cashflow(sender, instance, **kwargs):
    try:
        CashFlowTransaction.objects.filter(related_exchange=instance).delete()
    except Exception as e:
        print(f"❌ Exchange delete error: {e}")

# ==================== TELEFON QAYTARISH ====================

@receiver(post_save, sender='sales.PhoneReturn')
def handle_phone_return_cashflow(sender, instance, created, **kwargs):
    """Telefon qaytarish - CREATE va UPDATE"""
    if instance.return_amount <= 0:
        CashFlowTransaction.objects.filter(related_return=instance).delete()
        return

    try:
        if created:
            CashFlowTransaction.objects.create(
                shop=instance.phone_sale.phone.shop,
                transaction_date=instance.return_date,
                transaction_type='phone_return',
                amount_usd=-instance.return_amount,
                amount_uzs=Decimal('0'),
                related_phone=instance.phone_sale.phone,
                related_phone_sale=instance.phone_sale,
                related_return=instance,
                description=f"Qaytarish: {instance.phone_sale.phone.phone_model}",
                notes=f"Mijoz: {instance.phone_sale.customer.name}\n{instance.reason}",
                created_by=instance.created_by
            )
        else:
            cashflow = CashFlowTransaction.objects.filter(related_return=instance).first()
            if cashflow:
                cashflow.transaction_date = instance.return_date
                cashflow.amount_usd = -instance.return_amount
                cashflow.description = f"Qaytarish: {instance.phone_sale.phone.phone_model}"
                cashflow.notes = f"Mijoz: {instance.phone_sale.customer.name}\n{instance.reason}"
                cashflow.save()
            else:
                CashFlowTransaction.objects.create(
                    shop=instance.phone_sale.phone.shop,
                    transaction_date=instance.return_date,
                    transaction_type='phone_return',
                    amount_usd=-instance.return_amount,
                    amount_uzs=Decimal('0'),
                    related_phone=instance.phone_sale.phone,
                    related_phone_sale=instance.phone_sale,
                    related_return=instance,
                    description=f"Qaytarish: {instance.phone_sale.phone.phone_model}",
                    notes=f"Mijoz: {instance.phone_sale.customer.name}\n{instance.reason}",
                    created_by=instance.created_by
                )
    except Exception as e:
        print(f"❌ PhoneReturn cashflow error: {e}")


@receiver(pre_delete, sender='sales.PhoneReturn')
def delete_phone_return_cashflow(sender, instance, **kwargs):
    try:
        CashFlowTransaction.objects.filter(related_return=instance).delete()
    except Exception as e:
        print(f"❌ PhoneReturn delete error: {e}")


# ==================== KUNLIK SOTUVCHI ====================

@receiver(post_save, sender='inventory.Phone')
def handle_daily_seller_cashflow(sender, instance, created, **kwargs):
    """Kunlik sotuvchi - CREATE va UPDATE"""

    # Agar daily_seller bo'lmasa, chiqib ketamiz
    if instance.source_type != 'daily_seller':
        return

    # Agar to'lov summasi yo'q bo'lsa, mavjud cashflow ni o'chirish
    if not instance.daily_payment_amount or instance.daily_payment_amount <= 0:
        CashFlowTransaction.objects.filter(
            related_phone=instance,
            transaction_type='daily_seller_payment'
        ).delete()
        return

    try:
        from django.utils import timezone
        trans_date = instance.created_at if isinstance(instance.created_at, date) else (
            instance.created_at.date() if hasattr(instance.created_at, 'date') else timezone.now().date()
        )

        if created:
            # Yangi telefon - yangi cashflow yaratish
            CashFlowTransaction.objects.create(
                shop=instance.shop,
                transaction_date=trans_date,
                transaction_type='daily_seller_payment',
                amount_usd=-instance.daily_payment_amount,
                amount_uzs=Decimal('0'),
                related_phone=instance,
                description=f"Kunlik: {instance.daily_seller.name if instance.daily_seller else 'N/A'}",
                notes=f"{instance.phone_model} {instance.memory_size}",
                created_by=instance.created_by
            )
        else:
            # Yangilanish - mavjud cashflow ni topish yoki yangi yaratish
            cashflow = CashFlowTransaction.objects.filter(
                related_phone=instance,
                transaction_type='daily_seller_payment'
            ).first()

            if cashflow:
                # Mavjud cashflow ni yangilash
                cashflow.transaction_date = trans_date
                cashflow.amount_usd = -instance.daily_payment_amount
                cashflow.description = f"Kunlik: {instance.daily_seller.name if instance.daily_seller else 'N/A'}"
                cashflow.notes = f"{instance.phone_model} {instance.memory_size}"
                cashflow.save()
            else:
                # Agar cashflow topilmasa, yangi yaratish
                CashFlowTransaction.objects.create(
                    shop=instance.shop,
                    transaction_date=trans_date,
                    transaction_type='daily_seller_payment',
                    amount_usd=-instance.daily_payment_amount,
                    amount_uzs=Decimal('0'),
                    related_phone=instance,
                    description=f"Kunlik: {instance.daily_seller.name if instance.daily_seller else 'N/A'}",
                    notes=f"{instance.phone_model} {instance.memory_size}",
                    created_by=instance.created_by
                )

    except Exception as e:
        print(f"❌ DailySeller cashflow error: {e}")


@receiver(pre_delete, sender='inventory.Phone')
def delete_daily_seller_cashflow(sender, instance, **kwargs):
    """Telefon o'chirilganda Daily Seller cashflow ni o'chirish"""
    if instance.source_type == 'daily_seller':
        try:
            CashFlowTransaction.objects.filter(
                related_phone=instance,
                transaction_type='daily_seller_payment'
            ).delete()
        except Exception as e:
            print(f"❌ DailySeller delete error: {e}")


# ==================== XARAJATLAR ====================

@receiver(post_save, sender='sales.Expense')
def handle_expense_cashflow(sender, instance, created, **kwargs):
    """Xarajat - CREATE va UPDATE"""
    try:
        if created:
            CashFlowTransaction.objects.create(
                shop=instance.shop,
                transaction_date=instance.expense_date,
                transaction_type='daily_expense',
                amount_uzs=-instance.amount,
                amount_usd=Decimal('0'),
                related_expense=instance,
                description=f"Xarajat: {instance.name}",
                notes=instance.notes or '',
                created_by=instance.created_by
            )
        else:
            cashflow = CashFlowTransaction.objects.filter(related_expense=instance).first()
            if cashflow:
                cashflow.transaction_date = instance.expense_date
                cashflow.amount_uzs = -instance.amount
                cashflow.description = f"Xarajat: {instance.name}"
                cashflow.notes = instance.notes or ''
                cashflow.save()
            else:
                CashFlowTransaction.objects.create(
                    shop=instance.shop,
                    transaction_date=instance.expense_date,
                    transaction_type='daily_expense',
                    amount_uzs=-instance.amount,
                    amount_usd=Decimal('0'),
                    related_expense=instance,
                    description=f"Xarajat: {instance.name}",
                    notes=instance.notes or '',
                    created_by=instance.created_by
                )
    except Exception as e:
        print(f"❌ Expense cashflow error: {e}")


@receiver(pre_delete, sender='sales.Expense')
def delete_expense_cashflow(sender, instance, **kwargs):
    try:
        CashFlowTransaction.objects.filter(related_expense=instance).delete()
    except Exception as e:
        print(f"❌ Expense delete error: {e}")


@receiver(post_save, sender='inventory.SupplierPayment')
def handle_supplier_payment_cashflow(sender, instance, created, **kwargs):
    """
    Taminotchiga to'lov - FAQAT KASSA to'lovlari uchun Cash Flow
    Seyf to'lovlari Cash Flow'da ko'rinmaydi
    """
    from reports.models import CashFlowTransaction

    # ✅ FAQAT KASSA to'lovlari uchun
    if instance.payment_source != 'cash':
        # Agar seyf bo'lsa yoki payment_source yo'q bo'lsa, mavjud cashflow ni o'chirish
        CashFlowTransaction.objects.filter(
            related_supplier_payment=instance
        ).delete()
        return

    # ✅ To'lov summasi 0 yoki manfiy bo'lsa
    if instance.amount <= 0:
        CashFlowTransaction.objects.filter(
            related_supplier_payment=instance
        ).delete()
        return

    try:
        # ✅ ASOSIY O'ZGARISH - Shop ni to'g'ri topish
        # Payment modelida shop maydoni bor, to'g'ridan-to'g'ri ishlatamiz
        shop = instance.shop

        if not shop:
            print(f"⚠️ Supplier Payment {instance.id} uchun shop topilmadi")
            return

        if created:
            # ✅ YANGI KASSA TO'LOV - CHIQIM
            CashFlowTransaction.objects.create(
                shop=shop,
                transaction_date=instance.payment_date,
                transaction_type='supplier_payment_cash',
                amount_usd=-instance.amount,  # Manfiy - chiqim
                amount_uzs=Decimal('0'),
                related_supplier_payment=instance,
                description=f"💵 Kassa: {instance.supplier.name} ga to'lov",
                notes=f"Do'kon: {shop.name}\nTo'lov summasi: ${instance.amount}\nTo'lov turi: {instance.get_payment_type_display()}\n{instance.notes or ''}",
                created_by=instance.created_by
            )
            print(f"✅ Kassa to'lov cashflow yaratildi: ${instance.amount} - {shop.name}")
        else:
            # ✅ YANGILANISH
            # Avvalgi cashflow ni topish
            cashflow = CashFlowTransaction.objects.filter(
                related_supplier_payment=instance
            ).first()

            if cashflow:
                # Mavjud cashflow ni yangilash
                cashflow.shop = shop
                cashflow.transaction_date = instance.payment_date
                cashflow.amount_usd = -instance.amount
                cashflow.description = f"💵 Kassa: {instance.supplier.name} ga to'lov"
                cashflow.notes = f"Do'kon: {shop.name}\nTo'lov summasi: ${instance.amount}\nTo'lov turi: {instance.get_payment_type_display()}\n{instance.notes or ''}"
                cashflow.save()
                print(f"✅ Kassa to'lov cashflow yangilandi: ${instance.amount} - {shop.name}")
            else:
                # Yangi cashflow yaratish
                CashFlowTransaction.objects.create(
                    shop=shop,
                    transaction_date=instance.payment_date,
                    transaction_type='supplier_payment_cash',
                    amount_usd=-instance.amount,
                    amount_uzs=Decimal('0'),
                    related_supplier_payment=instance,
                    description=f"💵 Kassa: {instance.supplier.name} ga to'lov",
                    notes=f"Do'kon: {shop.name}\nTo'lov summasi: ${instance.amount}\nTo'lov turi: {instance.get_payment_type_display()}\n{instance.notes or ''}",
                    created_by=instance.created_by
                )
                print(f"✅ Kassa to'lov cashflow yaratildi (yangilashda): ${instance.amount} - {shop.name}")

    except Exception as e:
        print(f"❌ Supplier Payment Cashflow error: {e}")
        import traceback
        traceback.print_exc()


@receiver(pre_delete, sender='inventory.SupplierPayment')
def delete_supplier_payment_cashflow(sender, instance, **kwargs):
    """To'lov o'chirilganda Cash Flow ni o'chirish"""
    try:
        from reports.models import CashFlowTransaction
        deleted_count = CashFlowTransaction.objects.filter(
            related_supplier_payment=instance
        ).delete()[0]

        if deleted_count > 0:
            print(f"✅ Supplier payment cashflow o'chirildi: {deleted_count} ta")
    except Exception as e:
        print(f"❌ Supplier Payment delete error: {e}")
