import json
from datetime import datetime, timedelta
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from accounting.models import Lead, Entity, IndividualProfile, OrganizationProfile


# ___________________________________LEADS___________________________________________#
RESPONSE_WINDOW = timedelta(days=7)     # The Responsiveness gauge is empty after this time.
TEMPERATURES = Lead.Temperature.values  # From Ice to Hot, thus the index gives the level.
STATUS_TONE = {
    Lead.LeadStatus.NEW:         "busy",
    Lead.LeadStatus.OPEN:        "ok",
    Lead.LeadStatus.QUOTED:      "ok",
    Lead.LeadStatus.IN_PROGRESS: "low",
    Lead.LeadStatus.LOST:        "idle",
    Lead.LeadStatus.WON:         "ok",
}

def card_data(lead, now):
    """Put the data of the card on the lead: the names, the status tone,
    the values of the edit form, and the level (0 to 100) and the text
    of each gauge."""
    entity, owner = lead.entity, lead.entity.owner
    ind = getattr(entity, "individual_profile", None)
    org = getattr(entity, "organization_profile", None)
    lead.name = entity.display_name or entity.name
    lead.owner_name = (owner.get_full_name() or owner.username) if owner else ""
    lead.form_json = json.dumps({
        "name": entity.name, "type": entity.type, "owner": entity.owner_id,
        "email": entity.email, "phone": entity.phone, "address": entity.address,
        "description": lead.description, "stage": lead.stage, "status": lead.status,
        "size": lead.size, "qualifying_score": lead.qualifying_score,
        "temperature": lead.temperature, "turn": "yours" if lead.turn else "theirs",
        "responsiveness": timezone.localtime(lead.responsiveness).strftime("%Y-%m-%dT%H:%M")
                          if lead.responsiveness else None,
        # The values of the profile fields. The form shows them by type.
        "lastname": ind and ind.last_name, "birthdate": ind and ind.date_of_birth,
        "role": ind and ind.role_id, "title": ind and ind.title_id,
        "taxnumber": org and org.tax_number, "registration": org and org.registration_number,
        "url": org and org.url, "industry": org and org.industry_id,
    }, default=str)
    lead.tone = STATUS_TONE.get(lead.status, "idle")
    if lead.size is not None:
        lead.size_level = min(100, round(lead.size / 10))       # 1 to 1000
    lead.temp_level = TEMPERATURES.index(lead.temperature) * 100 // (len(TEMPERATURES) - 1)
    if lead.responsiveness:
        left = lead.responsiveness + RESPONSE_WINDOW - now
        lead.resp_level = min(100, max(0, round(left / RESPONSE_WINDOW * 100)))
        lead.resp_left = f"{left.days}d {left.seconds // 3600}h" if left > timedelta(0) else "Expired"

def leads(request):
    now = timezone.now()
    rows = list(Lead.objects.select_related(
        "entity__owner", "entity__individual_profile", "entity__organization_profile").order_by("-id"))
    for lead in rows:
        card_data(lead, now)

    return render(request, "sales/leads.html", {
        "page_title":   "Leads",
        "columns":      [{"title": label, "leads": [l for l in rows if l.stage == key]}
                         for key, label in Lead.SaleStage.choices if key != Lead.SaleStage.CLOSED],
        "closed_leads": [l for l in rows if l.stage == Lead.SaleStage.CLOSED],
    })

def save_lead(lead, post):
    """Copy the lead form to the lead and its entity, then save both. The
    New Lead overlay and the Edit Lead overlay use the same form."""
    when                = post.get("responsiveness")
    entity              = lead.entity
    entity.name         = post["name"]
    entity.description  = post.get("description","")
    entity.type         = post["type"]
    entity.owner_id     = post.get("owner") or None
    entity.email        = post.get("email", "")
    entity.phone        = post.get("phone", "")
    entity.address      = post.get("address", "")

    lead.description        = post.get("description", "")
    lead.stage              = post["stage"]
    lead.status             = post["status"]
    lead.size               = post.get("size") or 1
    lead.qualifying_score   = post.get("qualifying_score") or None
    lead.temperature        = post["temperature"]
    lead.responsiveness     = timezone.make_aware(datetime.fromisoformat(when)) if when else None
    lead.turn               = post.get("turn") == "yours"

    if lead.status in (Lead.LeadStatus.LOST, Lead.LeadStatus.WON):
        lead.stage = Lead.SaleStage.CLOSED 

    with transaction.atomic():
        entity.save()
        if entity.type == Entity.EntityType.INDIVIDUAL:
            OrganizationProfile.objects.filter(entity=entity).delete()
            IndividualProfile.objects.update_or_create(entity=entity, defaults={
                "first_name":    entity.name,
                "last_name":     post.get("lastname", ""),
                "date_of_birth": post.get("birthdate") or None,
                "role_id":       post.get("role") or None,
                "title_id":      post.get("title") or None,
            })
        else:
            IndividualProfile.objects.filter(entity=entity).delete()
            OrganizationProfile.objects.update_or_create(entity=entity, defaults={
                "legal_name":          entity.name,
                "tax_number":          post.get("taxnumber", ""),
                "registration_number": post.get("registration", ""),
                "url":                 post.get("url", ""),
                "industry_id":         post.get("industry") or None,
            })
        lead.save()

def lead_create(request):
    """The Save button of the New Lead overlay. It makes the entity and its lead."""
    if request.method == "POST":
        entity = Entity(company=request.company, created_by=request.user)   # Add to every function that creates a CompanyOwned record
        save_lead(Lead(company=request.company, entity=entity), request.POST)
        # The Quote and Invoice overlays send JSON. They select the new customer.
        if "application/json" in request.headers.get("Accept", ""):
            return JsonResponse({"id": entity.pk, "name": entity.name})
    return redirect("sales:leads")

def lead_update(request, pk):
    """The Save button of the Edit Lead overlay."""
    if request.method == "POST":
        save_lead(get_object_or_404(Lead.objects.select_related("entity"), pk=pk), request.POST)
    return redirect("sales:leads")

def dashboard(request):
    return render(request, "sales/dashboard.html")

def quotes(request):
    return render(request, "sales/quotes.html")

def invoices(request):
    return render(request, "sales/invoices.html")

def credit_notes(request):
    return render(request, "sales/credit_notes.html")

def partners(request):
    return render(request, "sales/partners.html")
