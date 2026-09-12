from accounting.models import JournalEntry
from accounting.date_range import default_range, get_range, label_of

def pending_entries(request):
    """The number of draft journal entries, for the side panel pill."""
    if not getattr(request, "company", None):
        return {}
    key, start, end = get_range(request)
    return {
        "pending_count": JournalEntry.objects.filter(
            status=JournalEntry.Status.DRAFT,
            date__range=(start, end),
        ).count()
    }

def date_range(request):
    """The values of the date range button in the module bar.
    The financial year dates give the default of the preset list."""
    if not getattr(request, "company", None):
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