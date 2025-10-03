# sales/forms.py
from datetime import timedelta

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from decimal import Decimal

from .models import PhoneSale, PhoneReturn, AccessorySale, PhoneExchange, Debt, DebtPayment, Expense
from inventory.models import Phone, PhoneModel, MemorySize
from shops.models import Customer, Shop


class DebtPaymentForm(forms.ModelForm):
    """Qarz to'lovi formi"""
    class Meta:
        model = DebtPayment
        fields = ['payment_amount', 'payment_date', 'notes']
        widgets = {
            'payment_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00',
                'required': True
            }),
            'payment_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Qo\'shimcha izohlar...'
            }),
        }
        labels = {
            'payment_amount': 'To\'lov summasi',
            'payment_date': 'To\'lov sanasi',
            'notes': 'Izohlar'
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.debt = kwargs.pop('debt', None)
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.fields['payment_date'].initial = timezone.now().date()

    def clean_payment_amount(self):
        amount = self.cleaned_data.get('payment_amount')

        if amount and self.debt:
            if amount <= 0:
                raise ValidationError("To'lov summasi musbat son bo'lishi kerak.")

            if amount > self.debt.remaining_amount:
                raise ValidationError(
                    f"To'lov summasi qarz qoldiqidan ({self.debt.currency_symbol}{self.debt.remaining_amount:.2f}) "
                    f"oshmasligi kerak."
                )

        return amount

    def save(self, commit=True):
        instance = super().save(commit=False)

        if self.debt:
            instance.debt = self.debt

        if commit:
            instance.save()
        return instance


class PhoneSaleForm(forms.ModelForm):
    """Telefon sotish formi - ikki tomonlama qarz bilan"""
    customer_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mijoz ismi',
            'id': 'id_customer_name'
        }),
        label="Mijoz ismi"
    )

    customer_phone = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+998901234567',
            'id': 'id_customer_phone'
        }),
        label="Mijoz telefon raqami"
    )

    debt_due_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'id': 'id_debt_due_date'
        }),
        label="Qarz qaytarish muddati"
    )

    class Meta:
        model = PhoneSale
        fields = [
            'phone', 'sale_price', 'cash_amount', 'card_amount',
            'credit_amount', 'debt_amount', 'sale_date', 'notes'
        ]
        widgets = {
            'phone': forms.HiddenInput(),
            'sale_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Sotish narxi ($)',
                'id': 'id_sale_price'
            }),
            'cash_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'value': 0,
                'id': 'id_cash_amount'
            }),
            'card_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'value': 0,
                'id': 'id_card_amount'
            }),
            'credit_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'value': 0,
                'id': 'id_credit_amount'
            }),
            'debt_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '500',
                'value': 0,
                'id': 'id_debt_amount'
            }),
            'sale_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'id': 'id_sale_date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Izoh...'
            })
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.fields['sale_date'].initial = timezone.now().date()
            self.fields['debt_due_date'].initial = timezone.now().date() + timedelta(days=30)
        else:
            if self.instance.sale_date:
                self.fields['sale_date'].initial = self.instance.sale_date.strftime('%Y-%m-%d')

            if self.instance.customer:
                self.fields['customer_name'].initial = self.instance.customer.name
                self.fields['customer_phone'].initial = self.instance.customer.phone_number

    def clean_phone(self):
        """✅ Telefon validatsiyasi"""
        phone = self.cleaned_data.get('phone')

        if not phone:
            raise ValidationError("Telefon tanlanishi kerak!")

        # Yangi yaratishda - faqat 'shop' va 'returned' statusli telefonlar
        if not self.instance.pk:
            if phone.status not in ['shop', 'returned']:
                raise ValidationError(
                    f"Bu telefon {phone.get_status_display()} holatida! "
                    f"Faqat do'kondagi yoki qaytarilgan telefonlarni sotish mumkin."
                )

        return phone

    def clean(self):
        cleaned_data = super().clean()
        sale_price = cleaned_data.get('sale_price')
        debt_amount = cleaned_data.get('debt_amount') or Decimal('0')
        debt_due_date = cleaned_data.get('debt_due_date')

        cash_amount = cleaned_data.get('cash_amount') or Decimal('0')
        card_amount = cleaned_data.get('card_amount') or Decimal('0')
        credit_amount = cleaned_data.get('credit_amount') or Decimal('0')

        if sale_price:
            total_payments = cash_amount + card_amount + credit_amount + debt_amount
            if abs(total_payments - sale_price) > Decimal('0.01'):
                raise ValidationError(
                    f"To'lovlar yig'indisi ({total_payments:.2f}$) sotish narxiga ({sale_price:.2f}$) teng bo'lishi kerak!"
                )

        if debt_amount > 0 and not debt_due_date:
            raise ValidationError({
                'debt_due_date': "Qarz uchun qaytarish muddati kiritilishi kerak!"
            })

        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        """Saqlash - ikki tomonlama qarz yaratish/yangilash"""
        is_new = not self.instance.pk
        phone_sale = super().save(commit=False)
        phone_sale.salesman = self.user

        # Mijozni yaratish/topish
        customer_phone = self.cleaned_data.get('customer_phone')
        customer_name = self.cleaned_data.get('customer_name')

        customer, created = Customer.objects.get_or_create(
            phone_number=customer_phone,
            defaults={'name': customer_name, 'created_by': self.user}
        )

        if not created and customer.name != customer_name:
            customer.name = customer_name
            customer.save(update_fields=['name'])

        phone_sale.customer = customer

        if commit:
            phone_sale.save()

            # Eski qarzlarni o'chirish (edit holatida)
            if not is_new:
                old_debt_amount = self.initial.get('debt_amount', Decimal('0'))
                if phone_sale.debt_amount != old_debt_amount:
                    # Mijoz → Sotuvchi qarzni o'chirish
                    Debt.objects.filter(
                        debt_type='customer_to_seller',
                        customer=self.instance.customer,
                        currency='USD',
                        notes__contains=phone_sale.phone.imei
                    ).delete()

                    # Sotuvchi → Boss qarzni o'chirish
                    shop_owner = phone_sale.phone.shop.owner
                    Debt.objects.filter(
                        debt_type='seller_to_boss',
                        debtor=self.user,
                        creditor=shop_owner,
                        currency='USD',
                        notes__contains=phone_sale.phone.imei
                    ).delete()

            # Yangi qarzlarni yaratish (agar qarz mavjud bo'lsa)
            if phone_sale.debt_amount > 0:
                debt_due_date = self.cleaned_data.get('debt_due_date')
                shop_owner = phone_sale.phone.shop.owner

                # Mijoz → Sotuvchi qarz
                Debt.objects.create(
                    debt_type='customer_to_seller',
                    creditor=self.user,
                    customer=phone_sale.customer,
                    currency='USD',
                    debt_amount=phone_sale.debt_amount,
                    paid_amount=Decimal('0'),
                    due_date=debt_due_date,
                    status='active',
                    notes=f"Telefon sotish {'(tahrirlangan)' if not is_new else ''}: {phone_sale.phone.phone_model} {phone_sale.phone.memory_size} (IMEI: {phone_sale.phone.imei})"
                )

                # Sotuvchi → Boss qarz (agar sotuvchi rahbar bo'lmasa)
                if self.user != shop_owner:
                    Debt.objects.create(
                        debt_type='seller_to_boss',
                        creditor=shop_owner,
                        debtor=self.user,
                        currency='USD',
                        debt_amount=phone_sale.debt_amount,
                        paid_amount=Decimal('0'),
                        due_date=debt_due_date,
                        status='active',
                        notes=f"Telefon sotish qarz javobgarligi {'(tahrirlangan)' if not is_new else ''}: {phone_sale.phone.phone_model} (Mijoz: {phone_sale.customer.name})"
                    )

        return phone_sale


class AccessorySaleForm(forms.ModelForm):
    """Aksessuar sotish formi - ikki tomonlama qarz bilan"""
    accessory_code = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Kod: 0001',
            'id': 'accessory_code_search'
        }),
        label="Aksessuar kodi"
    )

    customer_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mijoz ismi',
            'id': 'cust_name'
        }),
        label="Mijoz ismi"
    )

    customer_phone = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+998901234567',
            'id': 'cust_phone'
        }),
        label="Mijoz telefon raqami"
    )

    debt_due_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'id': 'id_accessory_debt_due_date'
        }),
        label="Qarz qaytarish muddati"
    )

    class Meta:
        model = AccessorySale
        fields = [
            'accessory', 'quantity', 'unit_price',
            'cash_amount', 'card_amount', 'credit_amount', 'debt_amount',
            'sale_date', 'notes'
        ]
        widgets = {
            'accessory': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_accessory',
                'style': 'display:none;'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'value': '1',
                'min': '1',
                'id': 'qty'
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'id': 'price',
                'placeholder': "Narx (so'm)"
            }),
            'cash_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'value': '0',
                'min': '0',
                'id': 'cash'
            }),
            'card_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'value': '0',
                'min': '0',
                'id': 'card'
            }),
            'credit_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'value': '0',
                'min': '0',
                'id': 'credit'
            }),
            'debt_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'value': '0',
                'min': '0',
                'max': '10000000',
                'id': 'debt'
            }),
            'sale_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'id': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Izoh...'
            })
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # ✅ TO'G'RI INITIAL QILISH - SANALAR
        if not self.instance.pk:
            # Yangi sotish
            self.initial['sale_date'] = timezone.now().date()
            self.initial['debt_due_date'] = timezone.now().date() + timedelta(days=30)
        else:
            # Edit paytida - mavjud sanalarni o'rnatish
            if self.instance.sale_date:
                self.initial['sale_date'] = self.instance.sale_date

            # Mijoz ma'lumotlari
            if self.instance.customer:
                self.initial['customer_name'] = self.instance.customer.name
                self.initial['customer_phone'] = self.instance.customer.phone_number

            # ✅ QARZ SANASINI INITIAL QILISH (agar qarz mavjud bo'lsa)
            if self.instance.debt_amount > 0:
                # Mijoz → Sotuvchi qarzini topish
                customer_debt = Debt.objects.filter(
                    debt_type='customer_to_seller',
                    customer=self.instance.customer,
                    creditor=self.instance.salesman,
                    currency='UZS',
                    notes__icontains=self.instance.accessory.name
                ).first()

                if customer_debt and customer_debt.due_date:
                    self.initial['debt_due_date'] = customer_debt.due_date.strftime('%Y-%m-%d')

    def clean(self):
        cleaned_data = super().clean()
        accessory = cleaned_data.get('accessory')
        customer_name = cleaned_data.get('customer_name')
        customer_phone = cleaned_data.get('customer_phone')
        quantity = cleaned_data.get('quantity')
        unit_price = cleaned_data.get('unit_price')

        cash_amount = cleaned_data.get('cash_amount') or Decimal('0')
        card_amount = cleaned_data.get('card_amount') or Decimal('0')
        credit_amount = cleaned_data.get('credit_amount') or Decimal('0')
        debt_amount = cleaned_data.get('debt_amount') or Decimal('0')
        debt_due_date = cleaned_data.get('debt_due_date')

        if not customer_name or not customer_name.strip():
            raise ValidationError({'customer_name': "Mijoz ismi kiritilishi kerak."})

        if not customer_phone or not customer_phone.strip():
            raise ValidationError({'customer_phone': "Telefon raqami kiritilishi kerak."})

        if not accessory:
            raise ValidationError({'accessory': "Aksessuar tanlanishi kerak."})

        if quantity and accessory:
            available_quantity = accessory.quantity
            if self.instance.pk:
                available_quantity += self.instance.quantity

            if quantity > available_quantity:
                raise ValidationError({
                    'quantity': f"Yetarli aksessuar yo'q! Mavjud: {available_quantity} dona"
                })

        if unit_price and quantity:
            total_price = unit_price * quantity
            total_payments = cash_amount + card_amount + credit_amount + debt_amount

            if abs(total_payments - total_price) > Decimal('1000'):
                raise ValidationError(
                    f"To'lovlar yig'indisi ({total_payments:,.0f} so'm) jami narxga ({total_price:,.0f} so'm) teng bo'lishi kerak!"
                )

        if debt_amount > 0 and not debt_due_date:
            raise ValidationError({
                'debt_due_date': "Qarz uchun qaytarish muddati kiritilishi kerak!"
            })

        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        """Saqlash - faqat yangi aksessuar sotish uchun qarz yaratish"""
        is_new = not self.instance.pk
        accessory_sale = super().save(commit=False)
        accessory_sale.salesman = self.user

        # Mijozni yaratish/topish
        customer_phone = self.cleaned_data.get('customer_phone')
        customer_name = self.cleaned_data.get('customer_name')

        customer, created = Customer.objects.get_or_create(
            phone_number=customer_phone,
            defaults={'name': customer_name, 'created_by': self.user}
        )

        if not created and customer.name != customer_name:
            customer.name = customer_name
            customer.save(update_fields=['name'])

        accessory_sale.customer = customer

        # Total priceni hisoblash
        accessory_sale.total_price = accessory_sale.unit_price * accessory_sale.quantity

        if commit:
            # Aksessuar sonini boshqarish
            if is_new:
                if accessory_sale.accessory.quantity < accessory_sale.quantity:
                    raise ValidationError(f"Yetarli aksessuar yo'q!")
                accessory_sale.accessory.quantity -= accessory_sale.quantity
                accessory_sale.accessory.save(update_fields=['quantity'])
            else:
                # Edit holatida - eski va yangi quantity farqini hisoblash
                old_quantity = self.initial.get('quantity', 0)
                quantity_diff = accessory_sale.quantity - old_quantity
                if quantity_diff != 0:
                    if quantity_diff > 0:
                        if accessory_sale.accessory.quantity < quantity_diff:
                            raise ValidationError(f"Yetarli aksessuar yo'q!")
                    accessory_sale.accessory.quantity -= quantity_diff
                    accessory_sale.accessory.save(update_fields=['quantity'])

            accessory_sale.save()

            # ✅ FAQAT YANGI SOTISH UCHUN QARZ YARATISH
            if is_new and accessory_sale.debt_amount > 0:
                debt_due_date = self.cleaned_data.get('debt_due_date')
                shop_owner = accessory_sale.accessory.shop.owner

                if self.user == shop_owner:
                    # Rahbar o'zi sotyapti
                    Debt.objects.create(
                        debt_type='customer_to_seller',
                        creditor=shop_owner,
                        customer=accessory_sale.customer,
                        currency='UZS',
                        debt_amount=accessory_sale.debt_amount,
                        paid_amount=Decimal('0'),
                        due_date=debt_due_date,
                        status='active',
                        notes=f"Aksessuar: {accessory_sale.accessory.name} x {accessory_sale.quantity}"
                    )
                else:
                    # Xodim sotyapti - ikki qarz

                    # a) MIJOZ → SOTUVCHI
                    Debt.objects.create(
                        debt_type='customer_to_seller',
                        creditor=self.user,
                        customer=accessory_sale.customer,
                        currency='UZS',
                        debt_amount=accessory_sale.debt_amount,
                        paid_amount=Decimal('0'),
                        due_date=debt_due_date,
                        status='active',
                        notes=f"Aksessuar: {accessory_sale.accessory.name} x {accessory_sale.quantity}"
                    )

                    # b) SOTUVCHI → BOSHLIQ
                    Debt.objects.create(
                        debt_type='seller_to_boss',
                        creditor=shop_owner,
                        debtor=self.user,
                        currency='UZS',
                        debt_amount=accessory_sale.debt_amount,
                        paid_amount=Decimal('0'),
                        due_date=debt_due_date,
                        status='active',
                        notes=f"Aksessuar qarz javobgarligi: {accessory_sale.accessory.name} (Mijoz: {accessory_sale.customer.name})"
                    )

        return accessory_sale


class PhoneExchangeForm(forms.ModelForm):
    """Telefon almashtirish formi - ikki tomonlama qarz bilan"""
    customer_name_input = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mijoz ismi',
            'id': 'id_customer_name_input'
        }),
        label="Mijoz ismi"
    )

    customer_phone_input = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+998901234567',
            'id': 'id_customer_phone_input'
        }),
        label="Mijoz telefon raqami"
    )

    debt_due_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'id': 'id_exchange_debt_due_date'
        }),
        label="Qarz qaytarish muddati"
    )

    class Meta:
        model = PhoneExchange
        fields = [
            'new_phone', 'new_phone_price', 'old_phone_model', 'old_phone_memory',
            'old_phone_imei', 'old_phone_condition_percentage', 'old_phone_accepted_price',
            'old_phone_repair_cost', 'old_phone_imei_cost', 'old_phone_future_sale_price',
            'old_phone_image', 'exchange_type', 'cash_amount', 'card_amount',
            'credit_amount', 'debt_amount', 'exchange_date', 'notes'
        ]

        widgets = {
            'new_phone': forms.HiddenInput(attrs={'id': 'id_new_phone'}),
            'new_phone_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'old_phone_model': forms.Select(attrs={'class': 'form-control'}),
            'old_phone_memory': forms.Select(attrs={'class': 'form-control'}),
            'old_phone_imei': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '15 raqamli IMEI'}),
            'old_phone_condition_percentage': forms.NumberInput(
                attrs={'class': 'form-control', 'min': 1, 'max': 100, 'value': 80}),
            'old_phone_accepted_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'old_phone_repair_cost': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'value': 0}),
            'old_phone_imei_cost': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'value': 0}),
            'old_phone_future_sale_price': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'old_phone_image': forms.FileInput(attrs={'class': 'form-control'}),
            'exchange_type': forms.Select(attrs={'class': 'form-control'}),
            'cash_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'value': 0}),
            'card_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'value': 0}),
            'credit_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'value': 0}),
            'debt_amount': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '500', 'value': 0}),
            'exchange_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['new_phone'].queryset = Phone.objects.filter(status='shop')

        if not self.instance.pk:
            self.fields['exchange_date'].initial = timezone.now().date()
            self.fields['debt_due_date'].initial = timezone.now().date() + timedelta(days=30)
        else:
            # Edit paytida sanalarni to'g'ri formatda initial qilish
            if self.instance.exchange_date:
                self.fields['exchange_date'].initial = self.instance.exchange_date.strftime('%Y-%m-%d')

            # Mijoz ma'lumotlarini initial qilish
            if self.instance.customer_name:
                self.fields['customer_name_input'].initial = self.instance.customer_name
            if self.instance.customer_phone_number:
                self.fields['customer_phone_input'].initial = self.instance.customer_phone_number

    def clean(self):
        cleaned_data = super().clean()
        customer_name = cleaned_data.get('customer_name_input')
        customer_phone = cleaned_data.get('customer_phone_input')
        debt_amount = cleaned_data.get('debt_amount') or Decimal('0')
        debt_due_date = cleaned_data.get('debt_due_date')

        if not customer_name or not customer_name.strip():
            raise ValidationError("Mijoz ismi kiritilishi kerak.")

        if not customer_phone or not customer_phone.strip():
            raise ValidationError("Mijoz telefon raqami kiritilishi kerak.")

        if debt_amount > 0 and not debt_due_date:
            raise ValidationError({
                'debt_due_date': "Qarz uchun qaytarish muddati kiritilishi kerak!"
            })

        cleaned_data['customer_name'] = customer_name.strip()
        cleaned_data['customer_phone_number'] = customer_phone.strip()

        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        exchange = super().save(commit=False)

        if self.user:
            exchange.salesman = self.user
            if not exchange.created_by:
                exchange.created_by = self.user

        if 'customer_name' in self.cleaned_data:
            exchange.customer_name = self.cleaned_data['customer_name']
        if 'customer_phone_number' in self.cleaned_data:
            exchange.customer_phone_number = self.cleaned_data['customer_phone_number']

        if exchange.customer_name and exchange.customer_phone_number and self.user:
            customer, created = Customer.objects.get_or_create(
                phone_number=exchange.customer_phone_number,
                defaults={
                    'name': exchange.customer_name,
                    'created_by': self.user
                }
            )

            if not created and customer.name != exchange.customer_name:
                customer.name = exchange.customer_name
                customer.save(update_fields=['name'])

            exchange.customer = customer

        if commit:
            exchange.save()

            # FAQAT YANGI YARATISHDA QARZ YARATISH
            is_new = not self.instance.pk

            if is_new and exchange.debt_amount > 0 and exchange.exchange_type == 'customer_pays':
                shop_owner = exchange.new_phone.shop.owner
                debt_due_date = self.cleaned_data.get('debt_due_date')

                if self.user == shop_owner:
                    # Rahbar o'zi almashtiryapti
                    Debt.objects.create(
                        debt_type='customer_to_seller',
                        creditor=shop_owner,
                        customer=exchange.customer,
                        currency='USD',
                        debt_amount=exchange.debt_amount,
                        paid_amount=Decimal('0'),
                        due_date=debt_due_date,
                        status='active',
                        notes=f"Telefon almashtirish: {exchange.old_phone_model} → {exchange.new_phone.phone_model}"
                    )
                else:
                    # Xodim almashtiryapti - ikki qarz

                    # a) MIJOZ → SOTUVCHI
                    Debt.objects.create(
                        debt_type='customer_to_seller',
                        creditor=self.user,
                        customer=exchange.customer,
                        currency='USD',
                        debt_amount=exchange.debt_amount,
                        paid_amount=Decimal('0'),
                        due_date=debt_due_date,
                        status='active',
                        notes=f"Telefon almashtirish: {exchange.old_phone_model} → {exchange.new_phone.phone_model}"
                    )

                    # b) SOTUVCHI → BOSHLIQ
                    Debt.objects.create(
                        debt_type='seller_to_boss',
                        creditor=shop_owner,
                        debtor=self.user,
                        currency='USD',
                        debt_amount=exchange.debt_amount,
                        paid_amount=Decimal('0'),
                        due_date=debt_due_date,
                        status='active',
                        notes=f"Almashtirish qarz javobgarligi: {exchange.new_phone.phone_model} (Mijoz: {exchange.customer.name})"
                    )

        return exchange

class PhoneReturnForm(forms.ModelForm):
    """Telefon qaytarish formi"""
    class Meta:
        model = PhoneReturn
        fields = ['phone_sale', 'return_amount', 'return_date', 'reason', 'notes']
        widgets = {
            'phone_sale': forms.HiddenInput(attrs={'required': True}),
            'return_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'required': True,
                'min': '0.01'
            }),
            'return_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'required': True,
                'placeholder': 'Qaytarish sababini kiriting...'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Qo\'shimcha izohlar (ixtiyoriy)'
            }),
        }
        labels = {
            'phone_sale': 'Telefon sotuvi',
            'return_amount': 'Qaytarilgan summa ($)',
            'return_date': 'Qaytarish sanasi',
            'reason': 'Qaytarish sababi',
            'notes': 'Izohlar'
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['phone_sale'].required = True
        self.fields['return_amount'].required = True
        self.fields['return_date'].required = True
        self.fields['reason'].required = True
        self.fields['notes'].required = False

        if user:
            self.fields['phone_sale'].queryset = PhoneSale.objects.filter(
                phone__status='sold'
            ).exclude(
                id__in=PhoneReturn.objects.values_list('phone_sale_id', flat=True)
            ).select_related('phone__phone_model', 'phone__memory_size', 'customer')

        if not self.instance.pk:
            self.fields['return_date'].initial = timezone.now().date()

    def clean_phone_sale(self):
        phone_sale = self.cleaned_data.get('phone_sale')

        if not phone_sale:
            raise ValidationError("Telefon sotuvini tanlash shart!")

        if not self.instance.pk:
            if PhoneReturn.objects.filter(phone_sale_id=phone_sale.id).exists():
                raise ValidationError("Bu telefon allaqachon qaytarilgan!")

        return phone_sale

    def clean_return_amount(self):
        return_amount = self.cleaned_data.get('return_amount')

        if not return_amount or return_amount <= 0:
            raise ValidationError("Qaytarish summasi 0 dan katta bo'lishi kerak!")

        return return_amount

    def clean_reason(self):
        reason = self.cleaned_data.get('reason', '').strip()

        if not reason:
            raise ValidationError("Qaytarish sababi kiritilishi kerak!")

        return reason

    def clean(self):
        cleaned_data = super().clean()
        phone_sale = cleaned_data.get('phone_sale')
        return_amount = cleaned_data.get('return_amount')

        if phone_sale and return_amount:
            if return_amount > phone_sale.sale_price:
                raise ValidationError({
                    'return_amount': f'Qaytarish summasi sotish narxidan (${phone_sale.sale_price}) katta bo\'lishi mumkin emas!'
                })

        return cleaned_data


# sales/forms.py (DebtForm qismi)
class DebtForm(forms.ModelForm):
    """Qarz formi - sotuvchi o'zi uchun qarz so'raydi"""

    class Meta:
        model = Debt
        fields = ['creditor', 'currency', 'debt_amount', 'due_date', 'notes']
        widgets = {
            'creditor': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_creditor',
                'required': True
            }),
            'currency': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'debt_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'Qarz summasi',
                'required': True
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Izohlar...'
            }),
        }
        labels = {
            'creditor': 'Kimdan qarz olyapsiz?',
            'currency': 'Valyuta',
            'debt_amount': 'Qarz summasi',
            'due_date': 'Qaytarish muddati',
            'notes': 'Izoh'
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Qarz beruvchilar ro'yxati (faqat boshliqlar)
        if self.user:
            boss_ids = Shop.objects.values_list('owner_id', flat=True).distinct()
            # O'zidan boshqa boshliqlarni ko'rsatish
            self.fields['creditor'].queryset = User.objects.filter(
                id__in=boss_ids
            ).exclude(id=self.user.id)

        # Majburiy maydonlar
        self.fields['due_date'].required = True
        self.fields['creditor'].required = True
        self.fields['debt_amount'].required = True
        self.fields['currency'].required = True

        # Default qiymatlar (faqat yangi yaratishda)
        if not self.instance.pk:
            self.fields['due_date'].initial = timezone.now().date() + timedelta(days=30)
            self.fields['currency'].initial = 'USD'

    def clean_creditor(self):
        creditor = self.cleaned_data.get('creditor')

        if not creditor:
            raise ValidationError("Qarz beruvchi (Boshliq) tanlanishi shart!")

        # O'zidan o'zi qarz ololmasligi
        if self.user and creditor == self.user:
            raise ValidationError("O'zingizdan o'zingizga qarz yarata olmaysiz!")

        return creditor

    def clean_debt_amount(self):
        debt_amount = self.cleaned_data.get('debt_amount')
        currency = self.cleaned_data.get('currency', 'USD')

        if not debt_amount or debt_amount <= 0:
            raise ValidationError("Qarz summasi 0 dan katta bo'lishi kerak!")

        # Valyuta bo'yicha maksimal summa
        if currency == 'USD' and debt_amount > 500:
            raise ValidationError("Dollar qarz summasi maksimal 500$ bo'lishi kerak!")
        elif currency == 'UZS' and debt_amount > 10000000:
            raise ValidationError("So'm qarz summasi maksimal 10,000,000 so'm bo'lishi kerak!")

        return debt_amount

    @transaction.atomic
    def save(self, commit=True):
        debt = super().save(commit=False)

        # Avtomatik o'rnatish
        debt.debt_type = 'seller_to_boss'
        debt.debtor = self.user
        debt.customer = None
        debt.master = None
        debt.status = 'active'
        debt.paid_amount = Decimal('0')

        if commit:
            debt.save()

        return debt


class ExpenseForm(forms.ModelForm):
    """Xarajat formi"""
    class Meta:
        model = Expense
        fields = ['shop', 'name', 'amount', 'expense_date', 'notes']
        widgets = {
            'shop': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Xarajat nomi'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '1000', 'min': '0', 'placeholder': "Summa (so'm)"}),
            'expense_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Izoh...'})
        }
        labels = {
            'amount': "Summa (so'm)",
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            self.fields['shop'].queryset = Shop.objects.filter(owner=self.user)
            if self.fields['shop'].queryset.count() == 1:
                self.fields['shop'].initial = self.fields['shop'].queryset.first()

        if not self.instance.pk:
            self.fields['expense_date'].initial = timezone.now().date()


class CustomerSearchForm(forms.Form):
    """Mijoz qidirish formi"""
    phone_number = forms.CharField(
        max_length=15,
        required=False,
        label="Telefon raqami bo'yicha qidirish",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+998901234567',
            'id': 'customerSearch'
        })
    )