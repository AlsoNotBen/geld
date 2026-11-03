"""The avatar of a user or an entity (a lead, a customer, a supplier).

    {% load avatar_tags %}
    {% avatar request.user %}            32 px, see .avatar in base.css
    {% avatar entity "sm" %}             24 px; also "lg" (56 px) and "xl" (96 px)
    {{ entity|avatar_url }}              the image URL, else ""

Without an image, the avatar shows the initials.
"""
from django import template
from django.urls import reverse
from django.utils.html import format_html

register = template.Library()


def is_user(obj):
    return hasattr(obj, "get_username")


@register.filter
def avatar_url(obj):
    if obj is None:
        return ""
    if is_user(obj):
        profile = getattr(obj, "profile", None)
        if profile and profile.avatar_id:
            return f'{reverse("user_avatar", args=[obj.pk])}?v={profile.avatar_id}'
        return ""
    if obj.avatar_id:
        return f'{reverse("filestore:download", args=[obj.avatar_id])}?inline'
    return ""


def initials(obj):
    if obj is None:
        return ""
    if is_user(obj):
        first, last = getattr(obj, "first_name", ""), getattr(obj, "last_name", "")
        if first or last:
            return (first[:1] + last[:1]).upper()
        return obj.get_username()[:2].upper()
    words = (obj.display_name or obj.name or "").split()
    return "".join(word[0] for word in words[:2]).upper()


@register.simple_tag
def avatar(obj, size=""):
    css = f"avatar avatar--{size}" if size else "avatar"
    url = avatar_url(obj)
    letters = initials(obj)
    if url:
        return format_html('<span class="{}" data-initials="{}"><img src="{}" alt="" loading="lazy"></span>',
                           css, letters, url)
    return format_html('<span class="{}" data-initials="{}" aria-hidden="true">{}</span>', css, letters, letters)
