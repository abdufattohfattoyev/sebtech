# reports/utils.py - TO'LIQ YANGILANGAN

from decimal import Decimal
from django.utils import timezone
from datetime import date, timedelta
from calendar import monthrange


class DateHelper:
    """Sana bilan ishlash"""

    @staticmethod
    def get_month_range(year, month):
        start_date = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end_date = date(year, month, last_day)
        return start_date, end_date

    @staticmethod
    def get_year_range(year):
        return date(year, 1, 1), date(year, 12, 31)


class NumberFormatter:
    """Raqamlarni formatlash"""

    @staticmethod
    def format_currency(amount, currency='UZS'):
        if isinstance(amount, (int, float, Decimal)):
            if currency == 'USD':
                return f"${amount:,.2f}"
            else:
                return f"{amount:,.0f} so'm"
        return f"0 {currency}"

    @staticmethod
    def format_percentage(value, decimal_places=2):
        if isinstance(value, (int, float, Decimal)):
            return f"{value:.{decimal_places}f}%"
        return "0.00%"

    @staticmethod
    def calculate_percentage_change(current, previous):
        if previous == 0:
            return Decimal('0.00')
        change = ((current - previous) / previous) * 100
        return Decimal(str(change)).quantize(Decimal('0.01'))


class CashFlowHelper:
    """Cash Flow helper"""

    @staticmethod
    def format_transaction_type(transaction_type):
        """Tranzaksiya turini formatlash"""
        types = {
            'phone_sale': '📱 Telefon sotildi',
            'accessory_sale': '🎧 Aksessuar sotildi',
            'exchange_income': '➕ Almashtirish (mijoz pul berdi)',
            'exchange_expense': '➖ Almashtirish (do\'kon pul berdi)',
            'exchange_equal': '🔄 Teng almashtirish',
            'daily_seller_payment': '💸 Kunlik sotuvchiga to\'lov',
            'phone_return': '↩️ Telefon qaytarish',
            'daily_expense': '💰 Kunlik harajat',
        }
        return types.get(transaction_type, transaction_type)

    @staticmethod
    def get_transaction_icon(transaction_type):
        """Tranzaksiya icon"""
        icons = {
            'phone_sale': '✅',
            'accessory_sale': '✅',
            'exchange_income': '➕',
            'exchange_expense': '➖',
            'exchange_equal': '🔄',
            'daily_seller_payment': '💸',
            'phone_return': '↩️',
            'daily_expense': '💰',
        }
        return icons.get(transaction_type, '•')

    @staticmethod
    def get_transaction_color(transaction_type):
        """Tranzaksiya rangi"""
        colors = {
            'phone_sale': 'success',
            'accessory_sale': 'success',
            'exchange_income': 'success',
            'exchange_expense': 'danger',
            'exchange_equal': 'info',
            'daily_seller_payment': 'danger',
            'phone_return': 'warning',
            'daily_expense': 'danger',
        }
        return colors.get(transaction_type, 'secondary')


class TemplateHelpers:
    """Template uchun helper"""

    @staticmethod
    def get_month_name(month_number):
        months = {
            1: 'Yanvar', 2: 'Fevral', 3: 'Mart', 4: 'Aprel',
            5: 'May', 6: 'Iyun', 7: 'Iyul', 8: 'Avgust',
            9: 'Sentabr', 10: 'Oktabr', 11: 'Noyabr', 12: 'Dekabr'
        }
        return months.get(month_number, '')

    @staticmethod
    def get_status_class(value, comparison_value=None):
        if comparison_value is None:
            return 'primary'
        if value > comparison_value:
            return 'success'
        elif value < comparison_value:
            return 'danger'
        else:
            return 'secondary'


class ExportHelper:
    """Export helper"""

    @staticmethod
    def prepare_data_for_export(report_data, report_type):
        return {
            'report_type': report_type,
            'generated_at': timezone.now().isoformat(),
            'shop': str(report_data.get('shop', '')),
            'period': report_data.get('date') or f"{report_data.get('month', '')}/{report_data.get('year', '')}",
            'sales': {
                'total_sales': float(report_data.get('sales', {}).get('total', 0)),
                'total_cash': float(report_data.get('sales', {}).get('cash', 0)),
                'total_card': float(report_data.get('sales', {}).get('card', 0)),
                'total_debt': float(report_data.get('sales', {}).get('debt', 0)),
            },
            'profits': {
                'phone_profit': float(report_data.get('profits', {}).get('phone_profit', 0)),
                'accessory_profit': float(report_data.get('profits', {}).get('accessory_profit', 0)),
                'exchange_profit': float(report_data.get('profits', {}).get('exchange_profit', 0)),
                'total_profit': float(report_data.get('profits', {}).get('total_profit', 0)),
            },
            'counts': {
                'phone_sales': report_data.get('counts', {}).get('phone', 0),
                'accessory_sales': report_data.get('counts', {}).get('accessory', 0),
                'exchanges': report_data.get('counts', {}).get('exchange', 0),
                'total_transactions': report_data.get('counts', {}).get('total', 0),
            },
            'cashflow': {
                'usd_income': float(report_data.get('cashflow', {}).get('usd', {}).get('income', 0)),
                'usd_expense': float(report_data.get('cashflow', {}).get('usd', {}).get('expense', 0)),
                'usd_net': float(report_data.get('cashflow', {}).get('usd', {}).get('net', 0)),
                'uzs_income': float(report_data.get('cashflow', {}).get('uzs', {}).get('income', 0)),
                'uzs_expense': float(report_data.get('cashflow', {}).get('uzs', {}).get('expense', 0)),
                'uzs_net': float(report_data.get('cashflow', {}).get('uzs', {}).get('net', 0)),
            }
        }

