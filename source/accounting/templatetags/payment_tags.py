"""The Record Payment overlay as a tag, for each page of the module."""

from django import template
from accounting.forms import PaymentForm

register = template.Library()


@register.inclusion_tag("accounting/_payment_form.html", takes_context=True)
def payment_form(context):
    request = context.get("request")
    company = getattr(request, "company", None)
    return {
        "csrf_token": context.get("csrf_token"),
        "form":       PaymentForm(company=company) if company else None,
    }
