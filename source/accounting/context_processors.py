from accounting.models import Document, JournalEntry
from accounting.date_range import default_range, get_range, label_of

def pending_entries(request):
    """The numbers of the side panel pills: the draft journal entries of the
    date range, and the draft bills that wait for approval (all dates, as the
    Review part of the Bills page)."""
    if not getattr(request, "company", None):
        return {}
    key, start, end = get_range(request)
    return {
        "pending_count": JournalEntry.objects.filter(company=request.company, status=JournalEntry.Status.DRAFT, date__range=(start, end)).count(),
        "pending_bills": Document.objects.filter(company=request.company, direction=Document.Direction.PURCHASE,
                                                 doc_type=Document.DocType.BILL, status=Document.Status.DRAFT).count(),
    }

def date_range(request):
    """Template context for the date-range button in the module bar.

    Financial-year bounds are the defaults offered by the preset list.
    Returns an empty dict when the request has no company attached.
    """
    if getattr(request, "company", None) is None:
        return {}

    key, start, end = get_range(request)
    fy_start, fy_end = default_range(request)

    return {
        "range_key":   key,
        "range_start": start,
        "range_end":   end,
        "range_label": label_of(key, start, end),
        "fy_start":    fy_start,
        "fy_end":      fy_end,
    }