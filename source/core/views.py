from django.contrib.auth.decorators import login_not_required
from django.http import HttpResponse
from django.template import loader

def index(request):
    template = loader.get_template("core/index.html")
    return HttpResponse(template.render({},request))


# The service worker must come from the root of the site. Its scope is
# then the full site. A file in /static/ can only control /static/.
@login_not_required
def service_worker(request):
    return HttpResponse(loader.render_to_string("sw.js"), content_type="application/javascript")


# The service worker keeps this page and shows it when the network is not
# available. Thus the page must open without a login.
@login_not_required
def offline(request):
    return HttpResponse(loader.render_to_string("offline.html"))
