from django import template

register = template.Library()

@register.filter
def get(dictionary, key):
    """
    Template filter to get dictionary value by key
    Usage: {{ dict|get:key }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)