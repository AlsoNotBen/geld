"""Template filters of the Inventory module."""

from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def qty(value, signed=False):
    """A quantity with no trailing zeros and a comma between the groups of
    three digits: 1,850 or 1.5. With signed, a change shows its sign: +40 or
    −6. No value is a dash.

    Example: {{ item.on_hand|qty }}   {{ row.change|qty:True }}
    """
    if value is None:
        return "—"
    value = Decimal(value)
    text = f"{abs(value).normalize():,f}"
    if value < 0:
        return "−" + text
    return f"+{text}" if signed and value > 0 else text
