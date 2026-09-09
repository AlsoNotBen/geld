class CurrentCompanyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.company = None
        if request.user.is_authenticated:
            membership = request.user.memberships.order_by("-is_default").first()
            if membership:
                request.company = membership.company
        return self.get_response(request)