from django import template

register = template.Library()

@register.filter
def dictsum(value, key=None):
    if isinstance(value, dict):
        if key:
            return sum(v.get(key, 0) for v in value.values() if isinstance(v, dict))
        return sum(value.values())
    return 0



@register.filter
def subtract(value, arg):
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

