from django import template

register = template.Library()

@register.filter
def split(value, arg):
    """Splits a string by a delimiter"""
    return value.split(arg)