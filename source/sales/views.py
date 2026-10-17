import json
from datetime import datetime, timedelta
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from accounting.date_range import get_range
from accounting.models import (Document, Entity, IndividualProfile, Lead, OrganizationProfile, customer_entities,
                               supplier_entities)
from accounting.views import ZERO, open_invoices, receivable_balances


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
    rows = list(Lead.objects.filter(company=request.company).select_related(
        "entity__owner", "entity__individual_profile", "entity__organization_profile").order_by("-id"))
    for lead in rows:
        card_data(lead, now)

    return render(request, "sales/leads.html", {
        "page_title":   "Leads",
        "columns":      [{"key": key, "title": label, "leads": [l for l in rows if l.stage == key]}
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

@require_POST
def lead_stage(request, pk):
    """The drop of a lead card on a column of the board. leads.js sends the
    stage of the column, and moves the card when the answer is OK."""
    stage = request.POST.get("stage")
    if stage not in Lead.SaleStage.values:
        return JsonResponse({"error": "Unknown stage."}, status=400)
    lead = get_object_or_404(Lead, pk=pk, company=request.company)
    lead.stage = stage
    lead.save(update_fields=["stage", "updated_at"])
    return JsonResponse({"stage": stage})

# ___________________________________DOCUMENTS_______________________________________#
# The tone of the status pill of a document (see .status--* in accounting.css).
DOCUMENT_TONE = {
    Document.Status.DRAFT:     "idle",
    Document.Status.SENT:      "busy",
    Document.Status.APPROVED:  "ok",
    Document.Status.PART_PAID: "low",
    Document.Status.PAID:      "ok",
    Document.Status.VOID:      "out",
}
# The tabs of the Quotes page. An approved quote is accepted. A void quote is closed.
QUOTE_TABS = {
    "open":     [Document.Status.DRAFT, Document.Status.SENT],
    "accepted": [Document.Status.APPROVED, Document.Status.PART_PAID, Document.Status.PAID],
    "closed":   [Document.Status.VOID],
}

def sales_documents(company, limit=None, **filters):
    """The sales documents of the company, the newest first. Each gets the tone of its status."""
    documents = list(Document.objects.filter(company=company, direction=Document.Direction.SALE, **filters)
                     .select_related("entity", "source_doc").prefetch_related("lines__tax_code")
                     .order_by("-date", "-id")[:limit])
    for document in documents:
        document.tone = DOCUMENT_TONE.get(document.status, "idle")
    return documents

def dashboard(request):
    """The position of the sales today: the open quotes and the open invoices.
    The credit notes are the credit notes of the date range that are not void.
    A credit note without an invoice is open credit."""
    _, start, end = get_range(request)
    company = request.company
    today = timezone.localdate()
    invoices = open_invoices(company)
    late = sorted((i for i in invoices if i.due and i.due < today), key=lambda i: i.due)
    credits = [c for c in sales_documents(company, doc_type=Document.DocType.CREDIT_NOTE, date__range=(start, end))
               if c.status != Document.Status.VOID]
    open_credits = [c for c in credits if not c.source_doc_id]
    return render(request, "sales/dashboard.html", {
        "open_quotes": sum((q.gross for q in sales_documents(company, doc_type=Document.DocType.QUOTE,
                                                             status__in=QUOTE_TABS["open"])), ZERO),
        "unpaid": sum((i.balance for i in invoices), ZERO),
        "late": late,
        "overdue": sum((i.balance for i in late), ZERO),
        "oldest_days": (today - late[0].due).days if late else None,
        "credit_total": sum((c.gross for c in credits), ZERO),
        "open_credits": open_credits,
        "open_credit_total": sum((c.gross for c in open_credits), ZERO),
        "partner_count": customer_entities(company).filter(is_active=True).count(),
        "recent": sales_documents(company, limit=6),
    })

def quotes(request):
    """The quotes of the date range in three tabs by status (see QUOTE_TABS)."""
    _, start, end = get_range(request)
    rows = sales_documents(request.company, doc_type=Document.DocType.QUOTE, date__range=(start, end))
    tabs = {key: [q for q in rows if q.status in statuses] for key, statuses in QUOTE_TABS.items()}
    return render(request, "sales/quotes.html", {
        **{f"{key}_quotes": documents for key, documents in tabs.items()},
        "open_total": sum((q.gross for q in tabs["open"]), ZERO),
        "accepted_total": sum((q.gross for q in tabs["accepted"]), ZERO),
    })

def credit_notes(request):
    """The credit notes of the date range. The source document of a credit note is the invoice that receives the credit."""
    _, start, end = get_range(request)
    rows = sales_documents(request.company, doc_type=Document.DocType.CREDIT_NOTE, date__range=(start, end))
    return render(request, "sales/credit_notes.html", {
        "credit_notes": rows,
        "total": sum((c.gross for c in rows if c.status != Document.Status.VOID), ZERO),
    })

def partners(request):
    """The customers of the business (see customer_entities). The balance is
    the money that the partner owes (see receivable_balances). A partner with
    supplier details or a bill is also a supplier."""
    company = request.company
    balances = receivable_balances(company)
    suppliers = set(supplier_entities(company).values_list("id", flat=True))
    return render(request, "sales/partners.html", {"partners": [{
        "id": entity.id,
        "name": entity.name,
        "is_supplier": entity.id in suppliers,
        "is_active": entity.is_active,
        "contact": entity.email or entity.phone,
        "balance": balances.get(entity.id, ZERO),
    } for entity in customer_entities(company)]})
