from django import forms
from django.contrib.auth.models import User
from .models import UserProfile
import re


class UserRegistrationForm(forms.ModelForm):
    """Yangi foydalanuvchi ro'yxatdan o'tkazish"""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Minimal 8 belgi'}),
        label="Parol",
        min_length=8,
        help_text="Kamida 8 ta belgi"
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Parolni takrorlang'}),
        label="Parol (takror)",
        min_length=8,
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        labels = {
            'username': 'Login',
            'first_name': 'Ism',
            'last_name': 'Familiya',
            'email': 'Email',
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'username'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ism'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Familiya'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Bu login band!")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Parollar mos emas!")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):
    """Foydalanuvchini tahrirlash"""
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Yangi parol'}),
        label="Yangi parol (ixtiyoriy)",
        required=False,
        min_length=8,
        help_text="Parolni o'zgartirmoqchi bo'lsangiz kiriting"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Parolni takrorlang'}),
        label="Parolni tasdiqlang",
        required=False,
        min_length=8,
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active']
        labels = {
            'first_name': 'Ism',
            'last_name': 'Familiya',
            'email': 'Email',
            'is_active': 'Faol',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password or confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError("Parollar mos kelmadi!")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get('new_password')
        if new_password:
            user.set_password(new_password)
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    """Profil ma'lumotlari"""

    class Meta:
        model = UserProfile
        fields = [
            'role', 'phone_number', 'avatar',
            'base_salary_usd', 'base_salary_uzs',
            'phone_commission_percent', 'accessory_commission_percent', 'exchange_commission_percent'
        ]
        labels = {
            'role': 'Rol',
            'phone_number': 'Telefon',
            'avatar': 'Rasm',
            'base_salary_usd': 'Asosiy maosh ($)',
            'base_salary_uzs': 'Asosiy maosh (so\'m)',
            'phone_commission_percent': 'Telefon komissiya (%)',
            'accessory_commission_percent': 'Aksessuar komissiya (%)',
            'exchange_commission_percent': 'Almashtirish komissiya (%)',
        }
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+998901234567',
                'pattern': r'\+998[0-9]{9}',
                'title': 'Format: +998901234567'
            }),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
            'base_salary_usd': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00',
                'min': '0'
            }),
            'base_salary_uzs': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '0.00',
                'min': '0'
            }),
            'phone_commission_percent': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '5.00',
                'min': '0',
                'max': '100'
            }),
            'accessory_commission_percent': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '10.00',
                'min': '0',
                'max': '100'
            }),
            'exchange_commission_percent': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '5.00',
                'min': '0',
                'max': '100'
            }),
        }
        help_texts = {
            'phone_number': 'Format: +998901234567',
            'phone_commission_percent': 'Telefon foydasi foizi (Dollar) 0-100 oralig\'ida',
            'accessory_commission_percent': 'Aksessuar foydasi foizi (So\'m) 0-100 oralig\'ida',
            'exchange_commission_percent': 'Almashtirish foydasi foizi (Dollar) 0-100 oralig\'ida',
        }

    def clean_phone_number(self):
        """Telefon raqamni tozalash va formatlash"""
        phone = self.cleaned_data.get('phone_number')

        if not phone:
            return None

        # Faqat raqamlarni qoldirish
        digits = re.sub(r'\D', '', phone)

        # 998 bilan boshlanmasa, qo'shish
        if not digits.startswith('998'):
            if len(digits) == 9:
                digits = '998' + digits
            else:
                raise forms.ValidationError("Telefon raqam noto'g'ri formatda!")

        # Uzunlikni tekshirish
        if len(digits) != 12:
            raise forms.ValidationError("Telefon raqam 12 ta raqamdan iborat bo'lishi kerak!")

        # +998XXXXXXXXX formatida qaytarish
        return f'+{digits}'

    def clean_phone_commission_percent(self):
        """Telefon komissiya foizini tekshirish"""
        percent = self.cleaned_data.get('phone_commission_percent')
        if percent is not None:
            if percent < 0 or percent > 100:
                raise forms.ValidationError("Foiz 0 dan 100 gacha bo'lishi kerak!")
        return percent

    def clean_accessory_commission_percent(self):
        """Aksessuar komissiya foizini tekshirish"""
        percent = self.cleaned_data.get('accessory_commission_percent')
        if percent is not None:
            if percent < 0 or percent > 100:
                raise forms.ValidationError("Foiz 0 dan 100 gacha bo'lishi kerak!")
        return percent

    def clean_exchange_commission_percent(self):
        """Almashtirish komissiya foizini tekshirish"""
        percent = self.cleaned_data.get('exchange_commission_percent')
        if percent is not None:
            if percent < 0 or percent > 100:
                raise forms.ValidationError("Foiz 0 dan 100 gacha bo'lishi kerak!")
        return percent