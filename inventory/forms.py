from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import (
    Phone, Accessory, ExternalSeller, DailySeller,
    AccessoryPurchaseHistory, Supplier, SupplierPayment
)
from shops.models import Shop


def round_to_thousands(value):
    """Qiymatni mingga yaxlitlash: 101300 -> 101000"""
    if isinstance(value, (int, float, Decimal)):
        return (int(value) // 1000) * 1000
    return value


class SupplierForm(forms.ModelForm):
    """Taminotchi formasi"""

    class Meta:
        model = Supplier
        fields = ['name', 'phone_number', 'initial_debt', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Taminotchi nomi'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Telefon raqami'
            }),
            'initial_debt': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Boshlang\'ich qarz ($)',
                'value': '0'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Qo\'shimcha izoh...'
            }),
        }
        labels = {
            'initial_debt': 'Boshlang\'ich qarz ($) - ixtiyoriy'
        }
        help_texts = {
            'initial_debt': 'Tizimga kiritishdan OLDINGI qarz (0 qoldirish mumkin)'
        }

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number:
            phone_number = ''.join(filter(str.isdigit, phone_number))
            if len(phone_number) < 9:
                raise forms.ValidationError("Telefon raqami noto'g'ri formatda")
        return phone_number

    def clean_initial_debt(self):
        debt = self.cleaned_data.get('initial_debt')
        if debt is None:
            return Decimal('0.00')
        if debt < 0:
            raise forms.ValidationError("Qarz manfiy bo'lishi mumkin emas")
        return debt


class SupplierPaymentForm(forms.ModelForm):
    """Taminotchiga to'lov formasi"""

    selected_phones = forms.ModelMultipleChoiceField(
        queryset=Phone.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'phone-checkbox'
        }),
        label="Telefonlarni tanlang"
    )

    class Meta:
        model = SupplierPayment
        fields = ['shop', 'supplier', 'amount', 'payment_type', 'payment_source', 'payment_date', 'notes']
        widgets = {
            # ✅ YANGI - SHOP WIDGET
            'shop': forms.Select(attrs={
                'class': 'form-control',
                'id': 'shop_select'
            }),
            'supplier': forms.Select(attrs={
                'class': 'form-control',
                'id': 'supplier_select'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': 'To\'lov summasi ($)'
            }),
            'payment_type': forms.RadioSelect(attrs={
                'class': 'payment-type-radio'
            }),
            'payment_source': forms.RadioSelect(attrs={
                'class': 'payment-source-radio'
            }),
            'payment_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Izoh (ixtiyoriy)...'
            }),
        }

    def __init__(self, *args, **kwargs):
        supplier = kwargs.pop('supplier', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # ✅ SHOP TANLASH - foydalanuvchiga tegishli do'konlar
        if user:
            from shops.models import Shop
            if hasattr(user, 'userprofile') and user.userprofile.role in ['boss', 'finance']:
                self.fields['shop'].queryset = Shop.objects.all()
            else:
                self.fields['shop'].queryset = Shop.objects.filter(owner=user)

            # Agar bitta do'kon bo'lsa, avtomatik tanlash
            if self.fields['shop'].queryset.count() == 1:
                self.fields['shop'].initial = self.fields['shop'].queryset.first()

        if supplier:
            self.fields['supplier'].initial = supplier
            self.fields['supplier'].widget.attrs['readonly'] = True

            # Faqat qarzda turgan telefonlarni ko'rsatish
            debt_phones = Phone.objects.filter(
                supplier=supplier,
                source_type='supplier',
                payment_status__in=['debt', 'partial']
            ).order_by('created_at')

            self.fields['selected_phones'].queryset = debt_phones

    def clean(self):
        cleaned_data = super().clean()
        payment_type = cleaned_data.get('payment_type')
        selected_phones = cleaned_data.get('selected_phones')
        amount = cleaned_data.get('amount')
        supplier = cleaned_data.get('supplier')
        payment_source = cleaned_data.get('payment_source')
        shop = cleaned_data.get('shop')

        # ✅ DO'KON TEKSHIRISH
        if not shop:
            raise ValidationError({'shop': "Do'kon tanlanishi kerak"})

        # Agar tahrirlash bo'lsa, instance (eski to'lov) mavjud
        old_amount = Decimal('0.00')
        if self.instance and self.instance.pk:
            old_amount = self.instance.amount

        if not supplier:
            raise ValidationError({'supplier': 'Taminotchi tanlanishi kerak'})

        if not amount or amount <= 0:
            raise ValidationError({'amount': 'To\'lov summasi 0 dan katta bo\'lishi kerak'})

        # Joriy balansni hisoblash: eski to'lovni qaytarib, yangi qarzni hisoblaymiz
        adjusted_balance = supplier.balance + old_amount

        # Yangi to'lov summasi adjusted_balance dan oshmasligi kerak
        if amount > adjusted_balance:
            raise ValidationError({
                'amount': f'To\'lov summasi qarzdan ({adjusted_balance:.2f} $) oshib ketdi'
            })

        if payment_type == 'specific':
            if not selected_phones:
                raise ValidationError({
                    'selected_phones': 'Kamida bitta telefon tanlanishi kerak'
                })

            total_debt = sum(phone.debt_balance for phone in selected_phones)
            if amount > total_debt:
                raise ValidationError({
                    'amount': f'To\'lov summasi tanlangan telefonlar qarzidan ({total_debt:.2f} $) oshib ketdi'
                })

        return cleaned_data


class PhoneForm(forms.ModelForm):
    """Telefon formasi - DOLLAR"""

    external_seller_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tashqi sotuvchi (diler) ismi'
        }),
        label="Tashqi sotuvchi ismi"
    )

    external_seller_phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Telefon raqami',
            'id': 'external_seller_phone_input'
        }),
        label="Tashqi sotuvchi telefoni"
    )

    daily_seller_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Kunlik sotuvchi ismi'
        }),
        label="Kunlik sotuvchi ismi"
    )

    daily_seller_phone = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Telefon raqami',
            'id': 'daily_seller_phone_input'
        }),
        label="Kunlik sotuvchi telefoni"
    )

    created_at = forms.DateField(
        required=True,
        input_formats=['%Y-%m-%d'],
        widget=forms.DateInput(
            format='%Y-%m-%d',
            attrs={
                'class': 'form-control',
                'type': 'date'
            }
        ),
        label="Qo'shilgan sana *",
        error_messages={
            'required': "Qo'shilgan sana kiritilishi shart!",
            'invalid': "Noto'g'ri sana formati!"
        }
    )

    # QARZ MAYDONLARI
    is_debt = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'is_debt_checkbox'
        }),
        label="Qarzga olish"
    )

    class Meta:
        model = Phone
        fields = [
            'shop', 'phone_model', 'memory_size', 'imei', 'condition_percentage',
            'status', 'purchase_price', 'imei_cost', 'repair_cost', 'sale_price',
            'image', 'source_type', 'supplier', 'external_seller', 'daily_seller',
            'daily_payment_amount', 'exchange_value',
            'original_owner_name', 'original_owner_phone', 'created_at',
            'note'
        ]
        widgets = {
            'shop': forms.Select(attrs={'class': 'form-control'}),
            'phone_model': forms.Select(attrs={'class': 'form-control'}),
            'memory_size': forms.Select(attrs={'class': 'form-control'}),
            'imei': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '15 raqamli IMEI kiriting *',
                'required': 'required',
                'maxlength': '15',
                'pattern': '[0-9]{15}'
            }),
            'condition_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 100,
                'value': 100
            }),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'purchase_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Telefon narxi ($) *',
                'id': 'id_purchase_price',
                'required': 'required'
            }),
            'imei_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'value': 0,
                'placeholder': 'IMEI xarajatlari ($)'
            }),
            'repair_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'value': 0,
                'placeholder': "Ta'mirlash xarajatlari ($)"
            }),
            'sale_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Sotish narxi ($)'
            }),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'source_type': forms.Select(attrs={'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'external_seller': forms.Select(attrs={
                'class': 'form-control',
                'id': 'external_seller_select'
            }),
            'daily_seller': forms.HiddenInput(),
            'daily_payment_amount': forms.HiddenInput(),
            'exchange_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Almashtirish qiymati ($)'
            }),
            'original_owner_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Asl egasi ismi'
            }),
            'original_owner_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Asl egasi telefon raqami'
            }),
            'note': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Izoh...'
            })
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['imei'].required = True
        self.fields['purchase_price'].required = True

        if self.user:
            self.fields['shop'].queryset = Shop.objects.all()
            if self.fields['shop'].queryset.count() == 1:
                self.fields['shop'].initial = self.fields['shop'].queryset.first()

        if not self.instance.pk:
            self.fields['external_seller'].empty_label = "Mavjud tashqi sotuvchini tanlang"
            self.fields['supplier'].empty_label = "Taminotchini tanlang"
            self.fields['condition_percentage'].initial = 100
            self.fields['imei_cost'].initial = 0
            self.fields['repair_cost'].initial = 0
        else:
            if self.instance.created_at:
                self.fields['created_at'].initial = self.instance.created_at

            if self.instance.daily_seller:
                self.fields['daily_seller_name'].initial = self.instance.daily_seller.name
                self.fields['daily_seller_phone'].initial = self.instance.daily_seller.phone_number

            # Tahrirlashda qarz checkboxni o'chirish
            if 'is_debt' in self.fields:
                del self.fields['is_debt']

    def clean_imei(self):
        imei = self.cleaned_data.get('imei')

        if not imei or not imei.strip():
            raise ValidationError("IMEI kiritilishi shart!")

        imei = ''.join(filter(str.isdigit, imei))

        if len(imei) != 15:
            raise ValidationError("IMEI 15 ta raqamdan iborat bo'lishi kerak!")

        existing_phone = Phone.objects.filter(imei=imei)
        if self.instance.pk:
            existing_phone = existing_phone.exclude(pk=self.instance.pk)

        if existing_phone.exists():
            phone = existing_phone.first()
            raise ValidationError(
                f"⚠️ Bu IMEI allaqachon mavjud!\n"
                f"Telefon: {phone.phone_model} {phone.memory_size}\n"
                f"Do'kon: {phone.shop.name}\n"
                f"Holat: {phone.get_status_display()}"
            )

        return imei

    def clean_purchase_price(self):
        purchase_price = self.cleaned_data.get('purchase_price')
        if purchase_price is None or purchase_price < 0:
            raise ValidationError("Sotib olingan narx kiritilishi shart va 0 dan katta bo'lishi kerak")
        return purchase_price

    def clean_created_at(self):
        created_at = self.cleaned_data.get('created_at')
        if not created_at:
            raise ValidationError("Qo'shilgan sana kiritilishi shart!")
        return created_at

    def clean(self):
        cleaned_data = super().clean()
        source_type = cleaned_data.get('source_type')
        supplier = cleaned_data.get('supplier')
        external_seller = cleaned_data.get('external_seller')
        external_seller_name = cleaned_data.get('external_seller_name')
        external_seller_phone = cleaned_data.get('external_seller_phone')
        daily_seller_name = cleaned_data.get('daily_seller_name')
        daily_seller_phone = cleaned_data.get('daily_seller_phone')
        purchase_price = cleaned_data.get('purchase_price')
        original_owner_name = cleaned_data.get('original_owner_name')
        original_owner_phone = cleaned_data.get('original_owner_phone')
        shop = cleaned_data.get('shop')
        is_debt = cleaned_data.get('is_debt', False)

        if not shop:
            raise ValidationError({'shop': "Do'kon tanlanishi shart"})

        if source_type == 'supplier' and not supplier:
            raise ValidationError({'supplier': "Taminotchi manba turi uchun taminotchi tanlanishi kerak."})

        elif source_type == 'external_seller':
            if not external_seller and not (external_seller_name and external_seller_phone):
                raise ValidationError({
                    'external_seller_name': "Tashqi sotuvchi turi uchun mavjud sotuvchini tanlang yoki yangi ma'lumot kiriting.",
                    'external_seller_phone': "Telefon raqami kiritilishi kerak."
                })

        elif source_type == 'daily_seller':
            if not daily_seller_name or not daily_seller_name.strip():
                raise ValidationError({
                    'daily_seller_name': "Kunlik sotuvchi turi uchun ism kiritilishi kerak."
                })

            if not daily_seller_phone or not daily_seller_phone.strip():
                raise ValidationError({
                    'daily_seller_phone': "Telefon raqami kiritilishi kerak."
                })

            if not purchase_price or purchase_price <= 0:
                raise ValidationError({
                    'purchase_price': "Kunlik sotuvchi uchun sotib olingan narx kiritilishi kerak."
                })

            cleaned_data['daily_payment_amount'] = purchase_price
            cleaned_data['daily_seller'] = None

        elif source_type == 'exchange':
            if not (original_owner_name and original_owner_phone):
                raise ValidationError({
                    'original_owner_name': "Almashtirish uchun asl egasi ismi kiritilishi kerak.",
                    'original_owner_phone': "Almashtirish uchun asl egasi telefon raqami kiritilishi kerak."
                })

        # Qarz logikasini saqlash
        cleaned_data['_is_debt'] = is_debt

        return cleaned_data

    def save(self, commit=True):
        phone = super().save(commit=False)
        phone.created_at = self.cleaned_data['created_at']

        # ✅ AVVAL cost_price ni hisoblash
        phone.cost_price = (
                phone.purchase_price +
                (phone.imei_cost or Decimal('0')) +
                (phone.repair_cost or Decimal('0'))
        )

        # Qarz holati (faqat yangi telefon uchun)
        if not self.instance.pk and phone.source_type == 'supplier':
            is_debt = self.cleaned_data.get('_is_debt', False)
            if is_debt:
                phone.payment_status = 'debt'
                phone.paid_amount = Decimal('0')
            else:
                phone.payment_status = 'paid'
                phone.paid_amount = phone.cost_price

        # External seller
        if (phone.source_type == 'external_seller' and
                not self.cleaned_data.get('external_seller') and
                self.cleaned_data.get('external_seller_name') and
                self.cleaned_data.get('external_seller_phone')):
            external_seller, created = ExternalSeller.objects.get_or_create(
                phone_number=self.cleaned_data['external_seller_phone'],
                defaults={
                    'name': self.cleaned_data['external_seller_name'],
                    'created_by': self.user
                }
            )
            if not created:
                external_seller.name = self.cleaned_data['external_seller_name']
                external_seller.save(update_fields=['name'])
            phone.external_seller = external_seller

        # Daily seller
        if (phone.source_type == 'daily_seller' and
                self.cleaned_data.get('daily_seller_name') and
                self.cleaned_data.get('daily_seller_phone')):
            daily_seller, created = DailySeller.objects.get_or_create(
                phone_number=self.cleaned_data['daily_seller_phone'],
                defaults={
                    'name': self.cleaned_data['daily_seller_name'],
                    'created_by': self.user
                }
            )
            if not created:
                daily_seller.name = self.cleaned_data['daily_seller_name']
                daily_seller.save(update_fields=['name'])
            phone.daily_seller = daily_seller
            phone.daily_payment_amount = self.cleaned_data.get('daily_payment_amount') or self.cleaned_data.get(
                'purchase_price')

        if commit:
            phone.save()

        return phone


# Qolgan formalar o'zgarishsiz...
class AccessoryForm(forms.ModelForm):
    """Aksessuar formasi - SO'M"""

    existing_code = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mavjud kod (0001)',
            'id': 'existing_code_input'
        }),
        label="Mavjud Aksessuar Kodi",
        help_text="Mavjud aksessuar ustiga qo'shish uchun kodini kiriting"
    )

    purchase_price = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '1000',
            'min': '0',
            'placeholder': 'Tannarx (so\'m)'
        }),
        label="Tannarx (so'm)",
        help_text="Narx avtomatik mingga yaxlitlanadi"
    )

    quantity = forms.IntegerField(
        min_value=1,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'value': '1',
            'placeholder': 'Soni'
        }),
        label="Soni"
    )

    sale_price = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '1000',
            'min': '0',
            'placeholder': "Sotish narxi (so'm)"
        }),
        label="Sotish narxi (so'm)"
    )

    class Meta:
        model = Accessory
        fields = ['shop', 'name', 'code', 'image', 'supplier']
        widgets = {
            'shop': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Aksessuar nomi'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Kod (0001)'
            }),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            self.fields['shop'].queryset = Shop.objects.all()
            if self.fields['shop'].queryset.count() == 1:
                self.fields['shop'].initial = self.fields['shop'].queryset.first()

        if self.instance.pk:
            self.fields['existing_code'].widget = forms.HiddenInput()
            self.fields['quantity'].widget = forms.HiddenInput()
            self.fields['purchase_price'].widget = forms.HiddenInput()
            self.fields['sale_price'].required = True
            self.fields['sale_price'].initial = self.instance.sale_price
        else:
            self.fields['code'].required = False
            self.fields['quantity'].required = True
            self.fields['purchase_price'].required = True
            self.fields['sale_price'].required = True

    def clean_existing_code(self):
        existing_code = self.cleaned_data.get('existing_code')
        if existing_code:
            existing_code = ''.join(filter(str.isdigit, existing_code))
            if existing_code:
                existing_code = existing_code.zfill(4)
        return existing_code

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            code = ''.join(filter(str.isdigit, code))
            if not code:
                raise ValidationError("Kod faqat raqamlardan iborat bo'lishi kerak")
            if len(code) < 4:
                code = code.zfill(4)
            elif len(code) > 10:
                raise ValidationError("Kod 10 ta raqamdan ko'p bo'lishi mumkin emas")
        return code

    def clean_purchase_price(self):
        price = self.cleaned_data.get('purchase_price')
        if price:
            rounded_price = round_to_thousands(price)
            return Decimal(str(rounded_price))
        return price

    def clean_sale_price(self):
        price = self.cleaned_data.get('sale_price')
        if price:
            rounded_price = round_to_thousands(price)
            return Decimal(str(rounded_price))
        return price

    def clean(self):
        cleaned_data = super().clean()
        existing_code = cleaned_data.get('existing_code')
        shop = cleaned_data.get('shop')
        code = cleaned_data.get('code')
        quantity = cleaned_data.get('quantity')
        purchase_price = cleaned_data.get('purchase_price')
        sale_price = cleaned_data.get('sale_price')

        if self.instance.pk:
            if not sale_price or sale_price <= 0:
                raise ValidationError({'sale_price': "Sotish narxi kiritilishi kerak."})
            return cleaned_data

        if not quantity or quantity <= 0:
            raise ValidationError({'quantity': "Soni kiritilishi kerak va 0 dan katta bo'lishi kerak."})

        if not purchase_price or purchase_price <= 0:
            raise ValidationError({'purchase_price': "Tannarx kiritilishi kerak va 0 dan katta bo'lishi kerak."})

        if not sale_price or sale_price <= 0:
            raise ValidationError({'sale_price': "Sotish narxi kiritilishi kerak."})

        if existing_code and shop:
            try:
                existing_accessory = Accessory.objects.get(shop=shop, code=existing_code)
                self._existing_accessory = existing_accessory
                cleaned_data['code'] = None
            except Accessory.DoesNotExist:
                raise ValidationError({'existing_code': f"Kod '{existing_code}' topilmadi."})

        elif not existing_code and shop:
            if code and Accessory.objects.filter(shop=shop, code=code).exists():
                raise ValidationError({'code': f"Bu kod ({code}) allaqachon mavjud."})
            if not code:
                cleaned_data['code'] = Accessory.get_next_code(shop)

        if purchase_price and sale_price and sale_price < purchase_price:
            raise ValidationError({'sale_price': "Sotish narxi tannarxdan kam bo'lmasligi kerak"})

        return cleaned_data

    def save(self, commit=True):
        quantity = self.cleaned_data.get('quantity', 0)
        purchase_price = self.cleaned_data.get('purchase_price', Decimal('0'))
        sale_price = self.cleaned_data.get('sale_price')

        if self.instance.pk:
            accessory = super().save(commit=False)
            accessory.sale_price = sale_price
            if commit:
                accessory.save()
            return accessory

        if quantity <= 0:
            raise ValidationError("Soni 0 dan katta bo'lishi kerak")
        if purchase_price <= 0:
            raise ValidationError("Tannarx 0 dan katta bo'lishi kerak")

        if hasattr(self, '_existing_accessory'):
            existing = self._existing_accessory
            AccessoryPurchaseHistory.objects.create(
                accessory=existing,
                quantity=quantity,
                purchase_price=purchase_price,
                created_by=self.user
            )
            if sale_price:
                existing.sale_price = sale_price
            if commit:
                existing.save()
            return existing
        else:
            accessory = super().save(commit=False)
            accessory.created_by = self.user
            accessory.sale_price = sale_price
            if commit:
                accessory.save()
                AccessoryPurchaseHistory.objects.create(
                    accessory=accessory,
                    quantity=quantity,
                    purchase_price=purchase_price,
                    created_by=self.user
                )
            return accessory


class AccessoryAddQuantityForm(forms.Form):
    """Aksessuar soni qo'shish formasi - SO'M"""

    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'placeholder': "Qo'shilayotgan soni"
        }),
        label="Qo'shilayotgan soni"
    )

    purchase_price = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '1000',
            'min': '0',
            'placeholder': "Tannarx (so'm)"
        }),
        label="Tannarx (so'm)",
        help_text="Narx avtomatik mingga yaxlitlanadi"
    )

    sale_price = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '1000',
            'min': '0',
            'placeholder': "Yangi sotish narxi (so'm, ixtiyoriy)"
        }),
        label="Yangi sotish narxi",
        help_text="Sotish narxini yangilash uchun kiriting"
    )

    def clean_purchase_price(self):
        price = self.cleaned_data.get('purchase_price')
        if price:
            rounded_price = round_to_thousands(price)
            return Decimal(str(rounded_price))
        return price

    def clean_sale_price(self):
        price = self.cleaned_data.get('sale_price')
        if price:
            rounded_price = round_to_thousands(price)
            return Decimal(str(rounded_price))
        return price

    def clean(self):
        cleaned_data = super().clean()
        purchase_price = cleaned_data.get('purchase_price')
        sale_price = cleaned_data.get('sale_price')
        if purchase_price and sale_price and sale_price < purchase_price:
            raise ValidationError({'sale_price': "Sotish narxi tannarxdan kam bo'lishi mumkin emas"})
        return cleaned_data

    def save(self, accessory, user, commit=True):
        quantity = self.cleaned_data['quantity']
        purchase_price = self.cleaned_data['purchase_price']
        sale_price = self.cleaned_data.get('sale_price')

        history = AccessoryPurchaseHistory(
            accessory=accessory,
            quantity=quantity,
            purchase_price=purchase_price,
            created_by=user
        )

        if sale_price is not None:
            accessory.sale_price = sale_price

        if commit:
            history.save()
            accessory.save()

        return accessory