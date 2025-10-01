from django import template

register = template.Library()

@register.filter(name="subtract")
def subtract(value, arg):
    """Ikki sonni ayirish"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter(name="div")
def div(value, arg):
    """Ikki sonni bo‘lish"""
    try:
        return float(value) / float(arg) if float(arg) != 0 else 0
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter(name="mul")
def mul(value, arg):
    """Ikki sonni ko‘paytirish"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter(name="get_item")
def get_item(dictionary, key):
    """Dictionarydan kalit bo‘yicha qiymatni olish"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, "")
    return ""