# inventory/utils.py
from decimal import Decimal


def round_to_thousands(value):
    """
    Qiymatni mingga yaxlitlash
    Misol: 101300 -> 101000, 99800 -> 99000
    """
    if value is None:
        return Decimal('0')

    try:
        num_value = int(Decimal(str(value)))
        rounded = (num_value // 1000) * 1000
        return Decimal(str(rounded))
    except (ValueError, TypeError, ArithmeticError):
        return Decimal('0')


def format_currency_sum(value):
    """So'mda formatlash: 1000000 -> 1 000 000 so'm"""
    try:
        num = int(Decimal(str(value)))
        return f"{num:,} so'm".replace(',', ' ')
    except:
        return "0 so'm"


def format_currency_usd(value):
    """Dollarda formatlash: 1000 -> $1,000"""
    try:
        return f"${Decimal(str(value)):,.2f}"
    except:
        return "$0.00"