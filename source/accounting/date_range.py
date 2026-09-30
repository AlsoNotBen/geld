"""The global date range of the Accounting module.

The browser keeps the choice of the user in local storage. The same
script copies the value into a cookie. Thus the server reads the range
on each request, and a view can filter its queries.

Cookie format:  key|start|end     e.g.  fy|2026-03-01|2027-02-28
"""

from datetime import date, timedelta
from accounting.models import FiscalYear

COOKIE = "acct_range"
LABELS = {
    "fy":      "Current Financial Year",
    "fy_last": "Last Financial Year",
    "quarter": "Current Quarter",
    "month":   "Current Month",
    "ytd":     "Year to Date",
}


def default_range(request):
    """The current financial year. It is the default range."""
    today   = date.today()
    year    = (FiscalYear.objects.filter(company=getattr(request, "company", None),start_date__lte=today, end_date__gte=today).first())
    
    if year:
        return year.start_date, year.end_date
    
    return date(today.year, 1, 1), date(today.year, 12, 31)


def get_range(request):
    """The active range as (key, start, end)."""
    parts = request.COOKIES.get(COOKIE, "").split("|")

    if len(parts) == 3:
        try:
            return parts[0], date.fromisoformat(parts[1]), date.fromisoformat(parts[2])
        except ValueError:
            pass

    start, end = default_range(request)
    return "fy", start, end


def label_of(key, start, end):
    """The text of the button in the module bar."""
    return LABELS.get(key) or f"{start:%d %b %Y} – {end:%d %b %Y}"

def previous_range(start, end):
    """The period of the same length that ends the day before start.
    A range of full months moves back in months. Thus a year stays a
    year, and a quarter stays a quarter."""
    
    if start.day == 1 and (end + timedelta(days=1)).day == 1:
        months      = (end.year - start.year) * 12 + end.month - start.month + 1
        first       = start.month - 1 - months                # zero-based month, can be negative
        prev_start  = date(start.year + first // 12, first % 12 + 1, 1)

        return prev_start, start - timedelta(days=1)
    
    length = end - start + timedelta(days=1)
    return start - length, start - timedelta(days=1)