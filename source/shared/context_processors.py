from .models import Company


def companies(request):
    """The companies of the company switch in the ribbon (see base.html). Only
    the active companies of which the user is a member show."""
    if not request.user.is_authenticated:
        return {}
    return {"user_companies": Company.objects.filter(memberships__user=request.user, is_active=True)}
