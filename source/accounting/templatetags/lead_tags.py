"""The New Lead overlay as a tag, for each page of the module."""

from django import template
from django.contrib.auth import get_user_model
from accounting.models import Lead, BusinessRole, Title, Industry

register = template.Library()


@register.inclusion_tag("accounting/_lead_form.html", takes_context=True)
def lead_form(context):
    return {
        "request":      context.get("request"),
        "csrf_token":   context.get("csrf_token"),
        "stages":       Lead.SaleStage.choices,
        "statuses":     Lead.LeadStatus.choices,
        "temperatures": Lead.Temperature.choices,
        "owners":       get_user_model().objects.filter(is_active=True),
        "roles":        BusinessRole.objects.all(),
        "titles":       Title.objects.all(),
        "industries":   Industry.objects.all(),
    }
