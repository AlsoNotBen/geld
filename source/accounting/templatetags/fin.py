"""Template filters of the financial statements."""

from django import template

register = template.Library()


@register.filter
def money(value):
    """A figure of a statement. A negative figure is in brackets. A zero
    is a dash."""
    if not value:
        return "\u2014"
    if value < 0:
        return f"({-value:,.2f})"
    return f"{value:,.2f}"