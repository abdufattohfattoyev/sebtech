# from django.db.models.signals import post_save, pre_delete
# from django.dispatch import receiver
# from inventory.models import Phone
# from django.db import transaction
# from datetime import date  # ✅ faqat date ishlatamiz
# from django.utils import timezone
# from reports.models import DailyReport, MonthlyReport, YearlyReport
#
#
# # def update_reports(shop, report_date):
# #     """Kunlik, oylik va yillik hisobotlarni yangilash — faqat date obyektlari bilan ishlaydi"""
# #     from django.core.exceptions import MultipleObjectsReturned
# #
# #     if not isinstance(report_date, date):
# #         return  # Agar sana bo'lmasa, hech narsa qilmasin
# #
# #     # Kunlik hisobot
# #     try:
# #         daily_report, created = DailyReport.objects.get_or_create(
# #             shop=shop,
# #             report_date=report_date  # ✅ DateField bilan to'g'ri ishlaydi
# #         )
# #     except MultipleObjectsReturned:
# #         daily_reports = DailyReport.objects.filter(
# #             shop=shop,
# #             report_date=report_date
# #         ).order_by('id')
# #         daily_report = daily_reports.first()
# #         daily_reports.exclude(id=daily_report.id).delete()
# #         created = False
# #
# #     daily_report.update_from_daily_data()
# #     daily_report.save()
# #
# #     # Oylik hisobot — oyning 1-sanasini olamiz
# #     month_start = date(report_date.year, report_date.month, 1)
# #     try:
# #         monthly_report, created = MonthlyReport.objects.get_or_create(
# #             shop=shop,
# #             report_month=month_start  # ✅ DateField
# #         )
# #     except MultipleObjectsReturned:
# #         monthly_reports = MonthlyReport.objects.filter(
# #             shop=shop,
# #             report_month=month_start
# #         ).order_by('id')
# #         monthly_report = monthly_reports.first()
# #         monthly_reports.exclude(id=monthly_report.id).delete()
# #         created = False
# #
# #     monthly_report.update_from_monthly_data()
# #     monthly_report.save()
# #
# #     # Yillik hisobot
# #     try:
# #         yearly_report, created = YearlyReport.objects.get_or_create(
# #             shop=shop,
# #             report_year=report_date.year  # ✅ IntegerField
# #         )
# #     except MultipleObjectsReturned:
# #         yearly_reports = YearlyReport.objects.filter(
# #             shop=shop,
# #             report_year=report_date.year
# #         ).order_by('id')
# #         yearly_report = yearly_reports.first()
# #         yearly_reports.exclude(id=yearly_report.id).delete()
# #         created = False
# #
# #     yearly_report.update_from_yearly_data()
# #     yearly_report.save()
#
#
# # @receiver(post_save, sender=Phone)
# # def update_reports_on_phone_save(sender, instance, created, **kwargs):
# #     if instance.created_at:
# #         update_reports(instance.shop, instance.created_at)  # ✅ DateField → date obyekti
# #
# #
# # @receiver(pre_delete, sender=Phone)
# # def update_reports_on_phone_delete(sender, instance, **kwargs):
# #     if instance.created_at:
# #         shop = instance.shop
# #         report_date = instance.created_at
# #         transaction.on_commit(lambda: update_reports(shop, report_date))