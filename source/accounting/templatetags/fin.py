"""Template filters of the financial statements."""

from django import template
from django.utils.html import format_html

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

@register.filter
def sparkline(values, tone=""):
    """An area graph of a short series, e.g. the 7 days of a week.

    Example: {{ trend|sparkline:"is-credit" }}
    The graph stretches to the width of its box. The CSS of .card__spark
    gives the size and the color.
    """
    values = [float(v or 0) for v in values or []]
    if len(values) < 2:
        return ""
    low, high = min(values), max(values)
    span = high - low
    step = 100 / (len(values) - 1)
    # The top 4 units stay free, thus the peak of the line is not clipped.
    # A flat series goes through the middle.
    points = " ".join(f"{i * step:.2f},{40 - ((v - low) / span * 34 if span else 17) - 2:.2f}"
                      for i, v in enumerate(values))
    return format_html(
        '<svg class="card__spark {}" viewBox="0 0 100 40" preserveAspectRatio="none" '
        'role="img" aria-label="Daily movement over the past {} days">'
        '<path class="spark__area" d="M0,40 L{} L100,40 Z"/>'
        '<polyline class="spark__line" points="{}" vector-effect="non-scaling-stroke"/>'
        '</svg>',
        tone, len(values), points.replace(" ", " L"), points,
    )
