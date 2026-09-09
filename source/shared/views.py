import random
import os
from django.conf import settings
from django.contrib.auth.views import LoginView

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