import random
import os
from django.conf import settings
from django.contrib.auth.views import LoginView
from django.db import transaction
from django import forms
from django.contrib import messages
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from accounting.setup import seed_company
from filestore.services import update_avatar

from .forms import AvatarField, CompanyForm
from .middleware import SESSION_KEY
from .models import Membership, UserProfile

BACKGROUND_DIR = settings.BASE_DIR / "static" / "img" / "login"

# The scan runs once, when Django imports this module.
LOGIN_BACKGROUNDS = sorted(
    f"img/login/{name}"
    for name in os.listdir(BACKGROUND_DIR)
    if name.lower().endswith((".jpg"))
)


class RandomBackgroundLoginView(LoginView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        #context["background"] = random.choice(LOGIN_BACKGROUNDS)
        context["background"] = "img/login/login-bg2.jpg"
        return context


@require_POST
def company_switch(request):
    """The company switch in the ribbon. The user must be a member of the
    company. The browser then goes back to the page, else to the home page."""
    company_id = request.POST.get("company", "")
    membership = company_id.isdigit() and Membership.objects.filter(
        user=request.user, company__is_active=True, company_id=company_id).first()
    if not membership:
        raise Http404("You are not a member of this company.")
    request.session[SESSION_KEY] = membership.company_id
    url = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()},
                                           require_https=request.is_secure()):
        url = reverse("index")
    return redirect(url)


@require_http_methods(["GET", "POST"])
def company_create(request):
    """The Add New Company overlay (see base.js). GET gives the empty form.
    POST makes the company, makes the user its owner, seeds its first-use
    data (see accounting.setup) and selects it. The answer is the form with
    the errors, or JSON with the page to go to."""
    form = CompanyForm(request.POST or None)
    if form.is_valid():
        with transaction.atomic():
            company = form.save()
            Membership.objects.create(user=request.user, company=company, role=Membership.Role.OWNER)
            seed_company(company, form.cleaned_data["fiscal_year_start"])
        request.session[SESSION_KEY] = company.pk
        return JsonResponse({"redirect": reverse("index")})
    return render(request, "shared/company_form.html", {"form": form})


def user_avatar(request, pk):
    """The avatar image of a user. Each signed-in user can see it."""
    profile = get_object_or_404(UserProfile.objects.select_related("avatar"), user_id=pk, avatar__isnull=False)
    return FileResponse(profile.avatar.file.open("rb"), filename=profile.avatar.original_name)


class ProfileForm(forms.Form):
    avatar = AvatarField()


@require_http_methods(["GET", "POST"])
def profile(request):
    """The Profile page of the user menu. The user uploads or removes an avatar."""
    form = ProfileForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        upload, clear = form.cleaned_data["avatar"], request.POST.get("avatar_clear")
        update_avatar(user_profile, upload, clear, request.user)
        if upload or clear:
            messages.success(request, "The avatar was saved." if upload else "The avatar was removed.")
        return redirect("profile")
    return render(request, "shared/profile.html", {"form": form})
