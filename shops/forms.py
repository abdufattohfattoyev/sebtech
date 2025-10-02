from django import forms
from .models import Shop, Customer
from users.models import UserProfile


class ShopForm(forms.ModelForm):
    class Meta:
        model = Shop
        fields = ['name', 'owner']
        labels = {
            'name': "Do'kon nomi",
            'owner': "Do'kon egasi",
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Do'kon nomini kiriting"}),
            'owner': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['owner'].queryset = UserProfile.objects.filter(role='boss').select_related('user')


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone_number', 'image', 'notes']
        labels = {
            'name': "Mijoz ismi",
            'phone_number': "Telefon raqami",
            'image': "Mijoz rasmi",
            'notes': "Izohlar",
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Mijoz ismini kiriting"}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "+998 XX XXX XX XX"}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': "Izohlar (ixtiyoriy)"}),
        }

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            cleaned_phone = ''.join(filter(str.isdigit, phone))
            if not cleaned_phone.startswith('998') or len(cleaned_phone) != 12:
                raise forms.ValidationError("Telefon raqami +998 bilan boshlanishi va 9 raqamdan iborat bo'lishi kerak!")
            return f"+{cleaned_phone[:3]} {cleaned_phone[3:5]} {cleaned_phone[5:8]} {cleaned_phone[8:]}"
        return phone
