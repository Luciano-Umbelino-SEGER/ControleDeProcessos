import os
from django import template

register = template.Library()

@register.filter
def basename(value):
    return os.path.basename(value)


@register.filter
def split(value, delimiter):
    if value:
        return value.split(delimiter)
    return []