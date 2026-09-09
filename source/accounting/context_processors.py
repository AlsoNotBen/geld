from accounting.models import JournalEntry

def pending_entries(request):
    """The number of draft journal entries, for the side panel pill."""
    if not getattr(request, "company", None):
        return {}
    return {
        "pending_count": JournalEntry.objects.filter(
            status=JournalEntry.Status.DRAFT
        ).count()
    }