from .models import Membership

# The session keeps the id of the company that the user selected (see shared.views.company_switch).
SESSION_KEY = "company_id"


class CurrentCompanyMiddleware:
    """Put the current company and the membership of the user on the request.

    The company comes from the session. The middleware always checks the
    membership, thus a request can never get a company of which the user
    is not a member. Without a valid selection, the default membership applies."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.company = None
        request.membership = None
        if request.user.is_authenticated:
            memberships = (Membership.objects.filter(user=request.user, company__is_active=True)
                           .select_related("company"))
            selected = request.session.get(SESSION_KEY)
            membership = ((selected and memberships.filter(company_id=selected).first())
                          or memberships.order_by("-is_default", "company__name").first())
            if membership:
                request.membership = membership
                request.company = membership.company
        return self.get_response(request)
