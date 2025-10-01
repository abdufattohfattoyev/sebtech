from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def div(value, arg):
    """Divide the value by the argument"""
    try:
        return float(value) / float(arg) if float(arg) != 0 else 0
    except (ValueError, TypeError):
        return 0

@register.filter
def sub(value, arg):
    """Subtract the argument from the value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def abs_filter(value):
    """Return absolute value"""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return 0