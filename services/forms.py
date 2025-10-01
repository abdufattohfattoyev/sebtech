# services/forms.py - To'g'irlangan

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .models import Master, MasterService, MasterPayment
from inventory.models import Phone


class MasterForm(forms.ModelForm):
    class Meta:
        model = Master
        fields = ['first_name', 'last_name', 'phone_number']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ism kiriting'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Familiya kiriting'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+998 90 123 45 67'
            }),
        }

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            cleaned = ''.join(filter(str.isdigit, phone))
            if len(cleaned) < 9 or len(cleaned) > 15:
                raise ValidationError("Telefon raqami 9-15 ta raqamdan iborat bo'lishi kerak!")
        return phone


class MasterServiceForm(forms.ModelForm):
    # YANGI: IMEI orqali telefon qidirish uchun
    phone_imei = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'IMEI orqali qidirish...',
            'id': 'phone_imei_search'
        }),
        label="Telefon IMEI"
    )

    class Meta:
        model = MasterService
        fields = ['phone', 'master', 'service_fee', 'repair_reasons', 'expected_return_date']
        widgets = {
            'phone': forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'Telefon tanlang'
            }),
            'master': forms.Select(attrs={
                'class': 'form-select',
                'data-placeholder': 'Usta tanlang'
            }),
            'service_fee': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00'
            }),
            'repair_reasons': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Ta\'mirlash sabablarini kiriting...'
            }),
            'expected_return_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Telefon maydonini sozlash
        if self.instance.pk:
            # Tahrirlashda - barcha do'kondagi telefonlar + joriy telefon
            phones = Phone.objects.filter(status='shop').select_related('phone_model', 'memory_size', 'shop')
            # Joriy telefonni ham qo'shish (agar master holatida bo'lsa)
            if self.instance.phone.status == 'master':
                phones = phones | Phone.objects.filter(pk=self.instance.phone.pk)
            self.fields['phone'].queryset = phones

            # IMEI maydoniga joriy telefon IMEI ni qo'yish
            self.fields['phone_imei'].initial = self.instance.phone.imei or ''
        else:
            # Yangi yaratishda - faqat do'kondagi telefonlar
            self.fields['phone'].queryset = Phone.objects.filter(
                status='shop'
            ).select_related('phone_model', 'memory_size', 'shop')

        # Usta tanlash
        self.fields['master'].queryset = Master.objects.all().order_by('first_name', 'last_name')

        # Telefon label
        self.fields['phone'].label_from_instance = lambda \
            obj: f"{obj.phone_model} {obj.memory_size} - IMEI: {obj.imei or 'N/A'}"

    def clean_service_fee(self):
        fee = self.cleaned_data.get('service_fee')
        if fee is not None and fee <= 0:
            raise ValidationError("Xizmat haqi 0 dan katta bo'lishi kerak!")
        return fee

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')

        if not phone:
            raise ValidationError("Telefon tanlash majburiy!")

        # Tahrirlashda eski telefon bilan solishtirib tekshirish
        if self.instance.pk:
            old_phone = self.instance.phone

            # Agar telefon o'zgartirilsa
            if phone != old_phone:
                # Yangi telefon do'konda bo'lishi kerak
                if phone.status != 'shop':
                    raise ValidationError("Yangi telefon do'konda bo'lishi kerak!")

                # Yangi telefon boshqa ustada emasligini tekshirish
                active_service = MasterService.objects.filter(
                    phone=phone,
                    status='in_progress'
                ).first()

                if active_service:
                    raise ValidationError(
                        f"Bu telefon allaqachon {active_service.master.full_name} ustada ta'mirlanmoqda!"
                    )
        else:
            # Yangi yaratishda telefon holatini tekshirish
            if phone.status != 'shop':
                raise ValidationError("Faqat do'kondagi telefonlarni tanlash mumkin!")

            # Telefon allaqachon boshqa ustada emasligini tekshirish
            active_service = MasterService.objects.filter(
                phone=phone,
                status='in_progress'
            ).first()

            if active_service:
                raise ValidationError(
                    f"Bu telefon allaqachon {active_service.master.full_name} ustada ta'mirlanmoqda!"
                )

        return phone


class MasterPaymentForm(forms.ModelForm):
    class Meta:
        model = MasterPayment
        fields = ['amount', 'payment_date', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00'
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
        self.master_service = kwargs.pop('master_service', None)
        super().__init__(*args, **kwargs)

        if self.master_service:
            # Qolgan summani hisoblash
            remaining = self.master_service.remaining_amount

            # Agar tahrirlash bo'lsa, joriy to'lovni hisobga olmaslik
            if self.instance.pk:
                remaining += self.instance.amount

            self.fields['amount'].widget.attrs['max'] = str(remaining)
            self.fields['amount'].help_text = f"Maksimal: ${remaining:.2f}"

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')

        if amount is not None and amount <= 0:
            raise ValidationError("To'lov summasi 0 dan katta bo'lishi kerak!")

        if self.master_service:
            # Qolgan summani hisoblash
            remaining = self.master_service.remaining_amount

            # Agar tahrirlash bo'lsa, joriy to'lovni hisobga olmaslik
            if self.instance.pk:
                remaining += self.instance.amount

            if amount > remaining:
                raise ValidationError(
                    f"To'lov summasi qolgan summadan katta bo'lishi mumkin emas! "
                    f"Maksimal: ${remaining:.2f}"
                )

        return amount