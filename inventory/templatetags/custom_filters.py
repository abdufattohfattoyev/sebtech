from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """Ko‘paytirish filteri: {{ price|mul:quantity }}"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''


@register.filter
def month_name_uz(value):
    """Oy raqamini o‘zbekcha nomiga o‘giradi"""
    months = {
        1: "Yanvar", 2: "Fevral", 3: "Mart", 4: "Aprel", 5: "May", 6: "Iyun",
        7: "Iyul", 8: "Avgust", 9: "Sentabr", 10: "Oktabr", 11: "Noyabr", 12: "Dekabr"
    }
    return months.get(value, str(value))


@register.filter
def sum_field(queryset, field_name):
    """QuerySet dan field qiymatlarini yig'ish"""
    try:
        return sum(getattr(obj, field_name, 0) or 0 for obj in queryset)
    except (AttributeError, TypeError):
        return 0
