# from django.contrib import admin
# from django.utils.html import format_html
# from django.db.models import Sum, Count
# from .models import DailyReport, MonthlyReport, YearlyReport, SalesmanMonthlyReport, DailySalesmanReport
# from sales.models import PhoneSale, AccessorySale, PhoneReturn
# import csv
# from django.http import HttpResponse
# from django.utils import timezone
# from django.urls import reverse
#
#
# def safe_int(value):
#     """Xavfsiz intga aylantirish — None yoki string bo'lsa 0 qaytaradi"""
#     try:
#         return int(float(value)) if value is not None else 0
#     except (ValueError, TypeError):
#         return 0
#
#
# @admin.register(SalesmanMonthlyReport)
# class SalesmanMonthlyReportAdmin(admin.ModelAdmin):
#     list_display = (
#         "salesman_info",
#         "report_month",
#         "phone_sales_summary",
#         "accessory_sales_summary",
#         "exchange_summary",
#         "total_summary",
#         "payment_summary",
#     )
#     list_filter = ("shop", "report_month", "salesman")
#     readonly_fields = (
#         "phones_sold_count", "phones_sold_total_value", "phones_sold_profit",
#         "phones_cash_amount", "phones_card_amount", "phones_credit_amount", "phones_debt_amount",
#         "accessories_sold_count", "accessories_sold_total_value", "accessories_sold_profit",
#         "accessories_cash_amount", "accessories_card_amount", "accessories_debt_amount",
#         "exchanges_count", "exchange_difference_total",
#         "exchange_cash_amount", "exchange_card_amount", "exchange_credit_amount", "exchange_debt_amount",
#         "total_sales_amount", "total_profit", "total_cash_received", "total_card_received",
#         "created_at", "updated_at"
#     )
#     search_fields = ("salesman__username", "salesman__first_name", "salesman__last_name", "shop__name")
#
#     def salesman_info(self, obj):
#         salesman_name = obj.salesman.get_full_name() or obj.salesman.username
#         return format_html(
#             '<strong>{}</strong><br/><small>{}</small>',
#             salesman_name, obj.shop.name
#         )
#
#     salesman_info.short_description = "Sotuvchi"
#
#     def phone_sales_summary(self, obj):
#         return format_html(
#             'Soni: <strong>{}</strong><br/>Summa: <span style="color: blue;">${}</span><br/>Foyda: <span style="color: green;">${}</span>',
#             obj.phones_sold_count or 0,
#             safe_int(obj.phones_sold_total_value),
#             safe_int(obj.phones_sold_profit)
#         )
#
#     phone_sales_summary.short_description = "Telefon sotuvlari"
#
#     def accessory_sales_summary(self, obj):
#         return format_html(
#             'Soni: <strong>{}</strong><br/>Summa: <span style="color: blue;">${}</span><br/>Foyda: <span style="color: green;">${}</span>',
#             obj.accessories_sold_count or 0,
#             safe_int(obj.accessories_sold_total_value),
#             safe_int(obj.accessories_sold_profit)
#         )
#
#     accessory_sales_summary.short_description = "Aksessuar sotuvlari"
#
#     def exchange_summary(self, obj):
#         return format_html(
#             'Soni: <strong>{}</strong><br/>Farq: <span style="color: orange;">${}</span>',
#             obj.exchanges_count or 0,
#             safe_int(obj.exchange_difference_total)
#         )
#
#     exchange_summary.short_description = "Almashtirishlar"
#
#     def total_summary(self, obj):
#         return format_html(
#             'Umumiy: <span style="color: blue;">${}</span><br/>Foyda: <span style="color: green;">${}</span>',
#             safe_int(obj.total_sales_amount),
#             safe_int(obj.total_profit)
#         )
#
#     total_summary.short_description = "Jami"
#
#     def payment_summary(self, obj):
#         return format_html(
#             'Naqd: <span style="color: green;">${}</span><br/>Karta: <span style="color: blue;">${}</span>',
#             safe_int(obj.total_cash_received),
#             safe_int(obj.total_card_received)
#         )
#
#     payment_summary.short_description = "To'lovlar"
#
#     actions = ['export_to_csv']
#
#     def export_to_csv(self, request, queryset):
#         response = HttpResponse(content_type='text/csv')
#         response['Content-Disposition'] = 'attachment; filename="salesman_monthly_reports.csv"'
#         writer = csv.writer(response)
#         writer.writerow([
#             "Do'kon", "Sotuvchi", "Hisobot oyi",
#             "Telefon soni", "Telefon summasi", "Telefon foydasi",
#             "Aksessuar soni", "Aksessuar summasi", "Aksessuar foydasi",
#             "Almashtirish soni", "Almashtirish farqi",
#             "Umumiy summa", "Umumiy foyda", "Umumiy naqd", "Umumiy karta"
#         ])
#         for report in queryset:
#             salesman_name = report.salesman.get_full_name() or report.salesman.username
#             writer.writerow([
#                 report.shop.name, salesman_name, report.report_month.strftime('%Y-%m'),
#                 report.phones_sold_count, safe_int(report.phones_sold_total_value), safe_int(report.phones_sold_profit),
#                 report.accessories_sold_count, safe_int(report.accessories_sold_total_value), safe_int(report.accessories_sold_profit),
#                 report.exchanges_count, safe_int(report.exchange_difference_total),
#                 safe_int(report.total_sales_amount), safe_int(report.total_profit),
#                 safe_int(report.total_cash_received), safe_int(report.total_card_received)
#             ])
#         return response
#
#     export_to_csv.short_description = "CSV ga eksport qilish"
#
#
# class DailySalesmanReportInline(admin.TabularInline):
#     model = DailySalesmanReport
#     extra = 0
#     readonly_fields = (
#         'salesman', 'phones_sold_count', 'phones_sold_total_value', 'phones_sold_profit',
#         'accessories_sold_count', 'accessories_sold_total_value', 'accessories_sold_profit',
#         'exchanges_count', 'exchange_difference_total', 'total_sales_amount', 'total_profit'
#     )
#     can_delete = False
#
#     def has_add_permission(self, request, obj=None):
#         return False
#
#
# @admin.register(DailySalesmanReport)
# class DailySalesmanReportAdmin(admin.ModelAdmin):
#     list_display = (
#         'salesman_name', 'report_date', 'phones_sold_count', 'accessories_sold_count',
#         'exchanges_count', 'total_sales_amount_display', 'total_profit_display'
#     )
#     list_filter = ('daily_report__report_date', 'daily_report__shop', 'salesman')
#     search_fields = ('salesman__first_name', 'salesman__last_name', 'salesman__username')
#     readonly_fields = (
#         'daily_report', 'salesman', 'phones_sold_count', 'phones_sold_total_value', 'phones_sold_profit',
#         'accessories_sold_count', 'accessories_sold_total_value', 'accessories_sold_profit',
#         'exchanges_count', 'exchange_difference_total', 'total_sales_amount', 'total_profit',
#         'created_at', 'updated_at'
#     )
#     ordering = ('-daily_report__report_date', '-total_sales_amount')
#
#     def salesman_name(self, obj):
#         return obj.salesman.get_full_name() or obj.salesman.username
#
#     salesman_name.short_description = 'Sotuvchi'
#     salesman_name.admin_order_field = 'salesman__first_name'
#
#     def report_date(self, obj):
#         return obj.daily_report.report_date
#
#     report_date.short_description = 'Sana'
#     report_date.admin_order_field = 'daily_report__report_date'
#
#     def total_sales_amount_display(self, obj):
#         return f"{safe_int(obj.total_sales_amount)}$"
#
#     total_sales_amount_display.short_description = 'Umumiy sotish'
#     total_sales_amount_display.admin_order_field = 'total_sales_amount'
#
#     def total_profit_display(self, obj):
#         return f"{safe_int(obj.total_profit)}$"
#
#     total_profit_display.short_description = 'Umumiy foyda'
#     total_profit_display.admin_order_field = 'total_profit'
#
#     def has_add_permission(self, request):
#         return False
#
#     def has_delete_permission(self, request, obj=None):
#         return False
#
#
# @admin.register(DailyReport)
# class DailyReportAdmin(admin.ModelAdmin):
#     list_display = (
#         'shop', 'report_date', 'phones_sold_count', 'accessories_sold_count', 'exchanges_count',
#         'total_profit_display', 'cash_balance_display', 'salesmen_count'
#     )
#     list_filter = ('shop', 'report_date')
#     search_fields = ('shop__name',)
#     readonly_fields = (
#         'phones_sold_count', 'phones_returned_count', 'phones_returned_total_value',
#         'accessories_sold_count', 'exchanges_count', 'phones_purchased_count',
#         'phones_purchased_total_value', 'phones_purchased_cash_paid',
#         'exchange_phones_accepted_count', 'exchange_phones_accepted_value',
#         'exchange_new_phones_sold_value', 'phone_sales_total', 'phone_sales_profit',
#         'accessory_sales_total', 'accessory_sales_profit', 'exchange_difference_total',
#         'total_expenses', 'cash_received', 'card_received', 'credit_amount',
#         'debt_amount', 'debt_payments_received', 'total_profit', 'cash_balance',
#         'cash_calculation_display', 'created_at'
#     )
#     ordering = ('-report_date',)
#     date_hierarchy = 'report_date'
#     inlines = [DailySalesmanReportInline]
#
#     fieldsets = (
#         ('Asosiy ma\'lumotlar', {
#             'fields': ('shop', 'report_date')
#         }),
#         ('Telefon sotuvlari', {
#             'fields': (
#                 'phones_sold_count', 'phone_sales_total', 'phone_sales_profit',
#                 'phones_returned_count', 'phones_returned_total_value'
#             )
#         }),
#         ('Aksessuar sotuvlari', {
#             'fields': (
#                 'accessories_sold_count', 'accessory_sales_total', 'accessory_sales_profit'
#             )
#         }),
#         ('Almashtirishlar', {
#             'fields': (
#                 'exchanges_count', 'exchange_difference_total',
#                 'exchange_phones_accepted_count', 'exchange_phones_accepted_value',
#                 'exchange_new_phones_sold_value'
#             )
#         }),
#         ('Telefon xaridlari', {
#             'fields': (
#                 'phones_purchased_count', 'phones_purchased_total_value', 'phones_purchased_cash_paid'
#             )
#         }),
#         ('To\'lovlar', {
#             'fields': (
#                 'cash_received', 'card_received', 'credit_amount', 'debt_amount', 'debt_payments_received'
#             )
#         }),
#         ('Xarajatlar va yakun', {
#             'fields': (
#                 'total_expenses', 'total_profit', 'cash_balance', 'cash_calculation_display'
#             )
#         }),
#         ('Texnik ma\'lumotlar', {
#             'fields': ('created_at',),
#             'classes': ('collapse',)
#         })
#     )
#
#     def total_profit_display(self, obj):
#         profit = safe_int(obj.total_profit)
#         color = 'green' if profit >= 0 else 'red'
#         return format_html(
#             '<span style="color: {}; font-weight: bold;">${}</span>',
#             color, profit
#         )
#
#     total_profit_display.short_description = 'Umumiy foyda'
#     total_profit_display.admin_order_field = 'total_profit'
#
#     def cash_balance_display(self, obj):
#         balance = safe_int(obj.cash_balance)
#         color = 'green' if balance >= 0 else 'red'
#         return format_html(
#             '<span style="color: {}; font-weight: bold;">${}</span>',
#             color, balance
#         )
#
#     cash_balance_display.short_description = 'Kassadagi naqd'
#     cash_balance_display.admin_order_field = 'cash_balance'
#
#     def salesmen_count(self, obj):
#         count = obj.salesman_reports.count()
#         if count > 0:
#             return format_html(
#                 '<a href="{}?daily_report__id={}">{} ta sotuvchi</a>',
#                 reverse('admin:reports_dailysalesmanreport_changelist'),
#                 obj.id, count
#             )
#         return "0 ta sotuvchi"
#
#     salesmen_count.short_description = 'Sotuvchilar'
#
#     actions = ['update_selected_reports']
#
#     def update_selected_reports(self, request, queryset):
#         updated = 0
#         for report in queryset:
#             report.update_from_daily_data()
#             updated += 1
#         self.message_user(request, f'{updated} ta kunlik hisobot yangilandi.')
#
#     update_selected_reports.short_description = 'Tanlangan hisobotlarni yangilash'
#
#
# @admin.register(MonthlyReport)
# class MonthlyReportAdmin(admin.ModelAdmin):
#     list_display = (
#         "shop",
#         "report_month",
#         "sales_summary",
#         "expenses_breakdown",
#         "payment_summary",
#         "debt_payments_received_display",
#         "cash_balance_display",
#         "total_income",
#         "total_profit_display",
#         "created_at",
#     )
#     list_filter = ("shop", "report_month")
#     readonly_fields = (
#         "phones_sold_count", "phones_returned_count", "phones_sold_total_value",
#         "phones_returned_total_value", "phones_sold_profit",
#         "accessories_sold_count", "accessories_sold_total_value", "accessories_sold_profit",
#         "exchanges_count", "exchange_difference_total",
#         "phones_purchased_count", "phones_purchased_total_value",
#         "cash_received", "card_received", "credit_amount", "debt_amount", "debt_payments_received",
#         "total_expenses", "imei_costs", "other_expenses",
#         "master_services_count", "master_services_total", "master_services_paid",
#         "total_revenue", "total_profit", "net_cash_flow", "created_at", "updated_at"
#     )
#     search_fields = ("shop__name",)
#     change_form_template = 'admin/reports/monthlyreport/change_form.html'
#
#     def sales_summary(self, obj):
#         return format_html(
#             'Tel: {} (${}) | Qaytarilgan: {} (${})<br/>'
#             'Aks: {} (${}) | Alm: {} (${})',
#             obj.phones_sold_count or 0, safe_int(obj.phones_sold_total_value),
#             obj.phones_returned_count or 0, safe_int(obj.phones_returned_total_value),
#             obj.accessories_sold_count or 0, safe_int(obj.accessories_sold_total_value),
#             obj.exchanges_count or 0, safe_int(obj.exchange_difference_total)
#         )
#
#     sales_summary.short_description = "Sotuvlar va qaytarishlar"
#
#     def expenses_breakdown(self, obj):
#         total_exp = safe_int(obj.total_expenses)
#         imei_costs = safe_int(obj.imei_costs)
#         other_exp = safe_int(obj.other_expenses)
#
#         imei_percentage = (imei_costs / total_exp * 100) if total_exp > 0 else 0
#         other_percentage = (other_exp / total_exp * 100) if total_exp > 0 else 0
#
#         return format_html(
#             'IMEI: <span style="color: orange;">${}</span> ({}%)<br/>'
#             'Boshqa: <span style="color: red;">${}</span> ({}%)<br/>'
#             'Jami: <strong>${}</strong>',
#             imei_costs, round(imei_percentage, 1),
#             other_exp, round(other_percentage, 1),
#             total_exp
#         )
#
#     expenses_breakdown.short_description = "Xarajatlar taqsimoti"
#
#     def payment_summary(self, obj):
#         return format_html(
#             'Naqd: <span style="color: green;">${}</span> | '
#             'Karta: <span style="color: blue;">${}</span><br/>'
#             'Nasiya: <span style="color: orange;">${}</span> | '
#             'Qarz: <span style="color: red;">${}</span>',
#             safe_int(obj.cash_received), safe_int(obj.card_received),
#             safe_int(obj.credit_amount), safe_int(obj.debt_amount)
#         )
#
#     payment_summary.short_description = "To'lovlar"
#
#     def debt_payments_received_display(self, obj):
#         return format_html('<span style="color: purple;">${}</span>', safe_int(obj.debt_payments_received))
#
#     debt_payments_received_display.short_description = "Olib kelingan qarz"
#
#     def cash_balance_display(self, obj):
#         net_cash = safe_int(obj.net_cash_flow)
#         color = "green" if net_cash >= 0 else "red"
#         return format_html('<span style="color: {}; font-weight: bold;">${}</span>', color, net_cash)
#
#     cash_balance_display.short_description = "Sof naqd oqim"
#
#     def total_income(self, obj):
#         total = (safe_int(obj.cash_received) + safe_int(obj.card_received) +
#                  safe_int(obj.credit_amount) + safe_int(obj.debt_amount))
#         return format_html('<span style="color: blue;">${}</span>', total)
#
#     total_income.short_description = "Umumiy daromad"
#
#     def total_profit_display(self, obj):
#         profit = safe_int(obj.total_profit)
#         color = "green" if profit >= 0 else "red"
#         return format_html('<span style="color: {}; font-weight: bold;">${}</span>', color, profit)
#
#     total_profit_display.short_description = "Umumiy foyda"
#
#     actions = ['refresh_reports', 'export_to_csv', 'view_salesman_reports']
#
#     def refresh_reports(self, request, queryset):
#         for report in queryset:
#             report.update_from_monthly_data()
#         self.message_user(request, f"{queryset.count()} ta oylik hisobot yangilandi")
#
#     refresh_reports.short_description = "Hisobotlarni yangilash"
#
#     def view_salesman_reports(self, request, queryset):
#         if queryset.count() == 1:
#             report = queryset.first()
#             salesman_reports = report.get_salesman_reports()
#             if salesman_reports.exists():
#                 message = f"{report.shop.name} - {report.report_month.strftime('%Y/%m')} - Sotuvchilar hisoboti:\n"
#                 for sr in salesman_reports:
#                     salesman_name = sr.salesman.get_full_name() or sr.salesman.username
#                     message += f"• {salesman_name}: Tel {sr.phones_sold_count}, Aks {sr.accessories_sold_count}, Jami ${safe_int(sr.total_sales_amount)}\n"
#                 self.message_user(request, message)
#             else:
#                 self.message_user(request, "Sotuvchilar hisoboti topilmadi")
#         else:
#             self.message_user(request, "Faqat bitta hisobotni tanlang", level='ERROR')
#
#     view_salesman_reports.short_description = "Sotuvchilar hisobotini ko'rish"
#
#     def export_to_csv(self, request, queryset):
#         response = HttpResponse(content_type='text/csv')
#         response['Content-Disposition'] = 'attachment; filename="monthly_reports.csv"'
#         writer = csv.writer(response)
#         writer.writerow([
#             "Do'kon", "Hisobot oyi", "Telefon sotuvlari soni", "Qaytarilgan telefonlar soni",
#             "Qaytarilgan telefonlar summasi", "Telefon sotuvlari summasi", "Telefon foydasi",
#             "Aksessuar sotuvlari soni", "Aksessuar sotuvlari summasi", "Aksessuar foydasi",
#             "Almashtirishlar soni", "Almashtirish summasi",
#             "Xarid qilingan telefonlar soni", "Xarid summasi", "Naqd", "Karta",
#             "Nasiya savdo", "Qarz savdo", "Olib kelingan qarz",
#             "Umumiy xarajatlar", "IMEI xarajatlari", "Boshqa xarajatlar",
#             "Usta xizmatlari soni", "Usta xizmatlari summasi", "Ustaga to'langan",
#             "Umumiy daromad", "Umumiy foyda", "Sof naqd oqim"
#         ])
#         for report in queryset:
#             writer.writerow([
#                 report.shop.name,
#                 report.report_month.strftime('%Y-%m'),
#                 report.phones_sold_count, report.phones_returned_count, safe_int(report.phones_returned_total_value),
#                 safe_int(report.phones_sold_total_value), safe_int(report.phones_sold_profit),
#                 report.accessories_sold_count, safe_int(report.accessories_sold_total_value), safe_int(report.accessories_sold_profit),
#                 report.exchanges_count, safe_int(report.exchange_difference_total),
#                 report.phones_purchased_count, safe_int(report.phones_purchased_total_value),
#                 safe_int(report.cash_received), safe_int(report.card_received), safe_int(report.credit_amount), safe_int(report.debt_amount),
#                 safe_int(report.debt_payments_received), safe_int(report.total_expenses), safe_int(report.imei_costs), safe_int(report.other_expenses),
#                 report.master_services_count, safe_int(report.master_services_total), safe_int(report.master_services_paid),
#                 safe_int(report.total_revenue), safe_int(report.total_profit), safe_int(report.net_cash_flow)
#             ])
#         return response
#
#     export_to_csv.short_description = "CSV ga eksport qilish"
#
#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related('shop')
#
#
# @admin.register(YearlyReport)
# class YearlyReportAdmin(admin.ModelAdmin):
#     list_display = (
#         "shop",
#         "report_year",
#         "sales_summary",
#         "payment_summary",
#         "debt_payments_received_display",
#         "total_income",
#         "total_profit_display",
#         "created_at",
#     )
#     list_filter = ("shop", "report_year")
#     readonly_fields = (
#         "phones_sold_count", "phones_returned_count", "phones_sold_total_value",
#         "phones_returned_total_value", "accessories_sold_count",
#         "accessories_sold_total_value", "exchanges_count", "exchange_difference_total",
#         "phones_purchased_count", "phones_purchased_total_value",
#         "debt_amount", "debt_payments_received", "total_revenue", "total_profit", "created_at",
#     )
#     search_fields = ("shop__name",)
#
#     def sales_summary(self, obj):
#         return format_html(
#             'Tel: {} (${}) | Qaytarilgan: {} (${})<br/>'
#             'Aks: {} (${}) | Alm: {} (${})',
#             obj.phones_sold_count or 0, safe_int(obj.phones_sold_total_value),
#             obj.phones_returned_count or 0, safe_int(obj.phones_returned_total_value),
#             obj.accessories_sold_count or 0, safe_int(obj.accessories_sold_total_value),
#             obj.exchanges_count or 0, safe_int(obj.exchange_difference_total)
#         )
#
#     sales_summary.short_description = "Sotuvlar va qaytarishlar"
#
#     def payment_summary(self, obj):
#         return format_html(
#             'Qarz berilgan: <span style="color: red;">${}</span>',
#             safe_int(obj.debt_amount)
#         )
#
#     payment_summary.short_description = "Qarzlar"
#
#     def debt_payments_received_display(self, obj):
#         return format_html('<span style="color: purple;">${}</span>', safe_int(obj.debt_payments_received))
#
#     debt_payments_received_display.short_description = "Olib kelingan qarz"
#
#     def total_income(self, obj):
#         total = (safe_int(obj.phones_sold_total_value) + safe_int(obj.accessories_sold_total_value) +
#                  safe_int(obj.exchange_difference_total))
#         return format_html('<span style="color: blue;">${}</span>', total)
#
#     total_income.short_description = "Umumiy daromad"
#
#     def total_profit_display(self, obj):
#         profit = safe_int(obj.total_profit)
#         color = "green" if profit >= 0 else "red"
#         return format_html('<span style="color: {}; font-weight: bold;">${}</span>', color, profit)
#
#     total_profit_display.short_description = "Umumiy foyda"
#
#     actions = ['refresh_reports', 'export_to_csv']
#
#     def refresh_reports(self, request, queryset):
#         for report in queryset:
#             report.update_from_yearly_data()
#         self.message_user(request, f"{queryset.count()} ta yillik hisobot yangilandi")
#
#     refresh_reports.short_description = "Hisobotlarni yangilash"
#
#     def export_to_csv(self, request, queryset):
#         response = HttpResponse(content_type='text/csv')
#         response['Content-Disposition'] = 'attachment; filename="yearly_reports.csv"'
#         writer = csv.writer(response)
#         writer.writerow([
#             "Do'kon", "Hisobot yili", "Telefon sotuvlari soni", "Qaytarilgan telefonlar soni",
#             "Qaytarilgan telefonlar summasi", "Telefon sotuvlari summasi",
#             "Aksessuar sotuvlari soni", "Aksessuar sotuvlari summasi",
#             "Almashtirishlar soni", "Almashtirish summasi",
#             "Xarid qilingan telefonlar soni", "Xarid summasi",
#             "Qarz berilgan", "Olib kelingan qarz", "Umumiy daromad", "Umumiy foyda"
#         ])
#         for report in queryset:
#             writer.writerow([
#                 report.shop.name,
#                 report.report_year,
#                 report.phones_sold_count, report.phones_returned_count, safe_int(report.phones_returned_total_value),
#                 safe_int(report.phones_sold_total_value),
#                 report.accessories_sold_count, safe_int(report.accessories_sold_total_value),
#                 report.exchanges_count, safe_int(report.exchange_difference_total),
#                 report.phones_purchased_count, safe_int(report.phones_purchased_total_value),
#                 safe_int(report.debt_amount), safe_int(report.debt_payments_received),
#                 safe_int(report.total_revenue), safe_int(report.total_profit)
#             ])
#         return response
#
#     export_to_csv.short_description = "CSV ga eksport qilish"
#
#     def get_queryset(self, request):
#         return super().get_queryset(request).select_related('shop')