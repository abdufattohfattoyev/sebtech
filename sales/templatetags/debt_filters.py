# sales/templatetags/debt_filters.py
from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def subtract(value, arg):
    """Ayirish operatsiyasi"""
    try:
        return Decimal(str(value)) - Decimal(str(arg))
    except (ValueError, TypeError):
        return Decimal('0')

@register.simple_tag
def calculate_balance(given, received):
    """Balansni hisoblash: bergan - olgan"""
    try:
        given_val = Decimal(str(given)) if given else Decimal('0')
        received_val = Decimal(str(received)) if received else Decimal('0')
        return given_val - received_val
    except (ValueError, TypeError):
        return Decimal('0')

@register.filter
def abs_value(value):
    """Absolyut qiymat"""
    try:
        return abs(Decimal(str(value)))
    except (ValueError, TypeError):
        return Decimal('0')