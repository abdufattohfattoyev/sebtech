from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from django.db import transaction
from django.db import models
from django.utils import timezone
from .models import Master, MasterService, MasterPayment

@admin.register(Master)
class MasterAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "phone_number",
        "active_repairs_count_display",
        "overdue_repairs_count_display",
        "total_unpaid_amount_display",
        "created_at"
    )
    search_fields = ("first_name", "last_name", "phone_number")
    list_filter = ("created_at",)
    readonly_fields = ("created_at",)

    # Fieldsets - faqat model fieldlari
    fieldsets = (
        ('Shaxsiy ma\'lumotlar', {
            'fields': ('first_name', 'last_name', 'phone_number')
        }),
        ('Tizim ma\'lumotlari', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = "Ism"

    def active_repairs_count_display(self, obj):
        # Master modelidagi barcha jarayondagi ishlarni hisoblash
        count = obj.master_services.filter(status='in_progress').count()
        if count > 0:
            return format_html('<span style="color: blue; font-weight: bold;">{}</span>', count)
        return "0"
    active_repairs_count_display.short_description = "Faol ishlar"

    def overdue_repairs_count_display(self, obj):
        # Muddat o'tgan ishlarni hisoblash
        from django.utils import timezone
        today = timezone.now().date()
        count = obj.master_services.filter(
            status='in_progress',
            expected_return_date__lt=today
        ).count()
        if count > 0:
            return format_html('<span style="color: red; font-weight: bold;">{}</span>', count)
        return "0"
    overdue_repairs_count_display.short_description = "Muddat o'tgan"

    def total_unpaid_amount_display(self, obj):
        # To'lanmagan summalari hisoblash
        unpaid = obj.total_unpaid_amount
        if unpaid > 0:
            return format_html('<span style="color: red;">${}</span>', int(unpaid))
        return "$0"
    total_unpaid_amount_display.short_description = "To'lanmagan summa"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('master_services')

    class MasterServiceInline(admin.TabularInline):
        model = MasterService
        extra = 0
        fields = ('phone', 'service_fee', 'paid_amount', 'status', 'given_date', 'expected_return_date')
        readonly_fields = ('paid_amount',)  # paid_amount avtomatik hisoblanadi

    inlines = [MasterServiceInline]

@admin.register(MasterService)
class MasterServiceAdmin(admin.ModelAdmin):
    list_display = (
        'phone_info',
        'master',
        'service_fee_display',
        'paid_amount_display',
        'remaining_amount_display',
        'status_display',
        'given_date',
        'expected_return_date',
        'is_overdue_display',
        'debt_info'
    )
    list_filter = ('status', 'master', 'given_date', 'expected_return_date')
    search_fields = (
        'phone__imei',
        'phone__phone_model__model_name',
        'master__first_name',
        'master__last_name',
        'repair_reasons'
    )
    readonly_fields = ('created_at', 'remaining_amount')

    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('phone', 'master', 'status')
        }),
        ('Ta\'mirlash ma\'lumotlari', {
            'fields': ('repair_reasons', 'service_fee', 'paid_amount')
        }),
        ('Sanalar', {
            'fields': ('given_date', 'expected_return_date')
        }),
        ('Tizim ma\'lumotlari', {
            'fields': ('created_at', 'debt'),
            'classes': ('collapse',)
        })
    )

    def phone_info(self, obj):
        if obj.phone.phone_model and obj.phone.memory_size:
            return format_html(
                '<strong>{} {}</strong><br/><small>IMEI: {}</small>',
                obj.phone.phone_model.model_name,
                obj.phone.memory_size.size,
                obj.phone.imei
            )
        return f"IMEI: {obj.phone.imei}"
    phone_info.short_description = "Telefon"

    def service_fee_display(self, obj):
        return format_html('<span style="color: blue;">${}</span>', int(obj.service_fee or 0))
    service_fee_display.short_description = "Xizmat haqi"

    def paid_amount_display(self, obj):
        if obj.paid_amount > 0:
            return format_html('<span style="color: green;">${}</span>', int(obj.paid_amount))
        return "$0"
    paid_amount_display.short_description = "To'langan"

    def remaining_amount_display(self, obj):
        remaining = obj.remaining_amount
        if remaining > 0:
            return format_html('<span style="color: red;">${}</span>', int(remaining))
        return "$0"
    remaining_amount_display.short_description = "Qolgan"

    def status_display(self, obj):
        if obj.status == 'in_progress':
            color = 'orange'
        else:
            color = 'green'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = "Holat"

    def is_overdue_display(self, obj):
        # Muddat o'tganligini tekshirish
        if obj.expected_return_date and obj.status == 'in_progress':
            today = timezone.now().date()
            if obj.expected_return_date < today:
                return format_html('<span style="color: red; font-weight: bold;">HA</span>')
        return "Yo'q"
    is_overdue_display.short_description = "Muddat o'tgan"

    def debt_info(self, obj):
        if obj.debt:
            creditor = obj.debt.creditor.get_full_name() or obj.debt.creditor.username
            return format_html(
                '<span style="color: purple;">Qarz: ${} | {}</span>',
                int(obj.debt.debt_amount or 0), creditor
            )
        return "Qarz yo'q"
    debt_info.short_description = "Qarz"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'phone__phone_model',
            'phone__memory_size',
            'master',
            'debt__creditor'
        )

    actions = ['mark_as_completed', 'recalculate_payments']

    def mark_as_completed(self, request, queryset):
        updated = 0
        with transaction.atomic():
            for obj in queryset:
                if obj.status != 'completed':
                    obj.status = 'completed'
                    obj.save()
                    updated += 1
        self.message_user(request, f'{updated} ta xizmat tugallangan deb belgilandi.')
    mark_as_completed.short_description = "Tugallangan deb belgilash"

    def recalculate_payments(self, request, queryset):
        """To'lovlarni qayta hisoblash"""
        updated = 0
        with transaction.atomic():
            for obj in queryset:
                # To'lovlarni qayta hisoblash
                total_paid = obj.payments.aggregate(
                    total=models.Sum('payment_amount')
                )['total'] or 0
                obj.paid_amount = total_paid
                obj.save()
                updated += 1
        self.message_user(
            request,
            f'{updated} ta xizmat uchun to\'lovlar qayta hisoblandi.',
            messages.SUCCESS
        )
    recalculate_payments.short_description = "To'lovlarni qayta hisoblash"

    class MasterPaymentInline(admin.TabularInline):
        model = MasterPayment
        extra = 0
        fields = ('payment_amount', 'paid_by', 'payment_date', 'notes')
        readonly_fields = ('payment_date',)

    inlines = [MasterPaymentInline]

@admin.register(MasterPayment)
class MasterPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "master_service_display",
        "phone_display",
        "payment_amount_display",
        "payment_date",
        "paid_by",
        "debt_status"
    )
    list_filter = ("payment_date", "paid_by", "master_service__master", "master_service__status")
    search_fields = (
        "master_service__master__first_name",
        "master_service__master__last_name",
        "master_service__phone__imei",
        "notes"
    )
    readonly_fields = ("payment_date",)

    fieldsets = (
        ('To\'lov ma\'lumotlari', {
            'fields': ('master_service', 'payment_amount', 'paid_by')
        }),
        ('Qo\'shimcha', {
            'fields': ('notes', 'payment_date'),
            'classes': ('collapse',)
        })
    )

    def master_service_display(self, obj):
        return format_html(
            '<strong>{}</strong><br/><small>{}</small>',
            f"{obj.master_service.master.first_name} {obj.master_service.master.last_name}",
            obj.master_service.get_status_display()
        )
    master_service_display.short_description = "Usta"

    def phone_display(self, obj):
        if obj.master_service.phone.phone_model and obj.master_service.phone.memory_size:
            return format_html(
                '{} {}<br/><small>IMEI: {}</small>',
                obj.master_service.phone.phone_model.model_name,
                obj.master_service.phone.memory_size.size,
                obj.master_service.phone.imei
            )
        return f"IMEI: {obj.master_service.phone.imei}"
    phone_display.short_description = "Telefon"

    def payment_amount_display(self, obj):
        return format_html('<span style="color: green;">${}</span>', int(obj.payment_amount or 0))
    payment_amount_display.short_description = "To'lov"

    def debt_status(self, obj):
        service = obj.master_service
        remaining = service.remaining_amount
        if remaining > 0:
            return format_html(
                '<span style="color: red;">Qolgan: ${}</span>',
                int(remaining)
            )
        return format_html('<span style="color: green;">To\'landi</span>')
    debt_status.short_description = "Qarz holati"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'master_service__master',
            'master_service__phone__phone_model',
            'master_service__phone__memory_size',
            'paid_by',
            'master_service__debt__creditor'
        )

    def save_model(self, request, obj, form, change):
        if not obj.paid_by:
            obj.paid_by = request.user
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """Model o'chirishda hisobotlarni yangilash"""
        with transaction.atomic():
            super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        """Ko'p obyektni o'chirishda hisobotlarni yangilash"""
        with transaction.atomic():
            super().delete_queryset(request, queryset)