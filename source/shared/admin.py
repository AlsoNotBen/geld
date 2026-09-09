from django.contrib import admin
from shared.models import *

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("alpha_code", "numeric_code", "name", "symbol", "minor_unit")
    search_fields = ("alpha_code", "name", "numeric_code")
    ordering = ("alpha_code",)


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ("source_currency", "target_currency", "quotation_date", "rate")
    list_filter = ("source_currency", "target_currency")
    search_fields = ("source_currency__alpha_code", "target_currency__alpha_code")
    date_hierarchy = "quotation_date"
    ordering = ("-quotation_date",)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "tax_number", "base_currency", "is_active", "created_at")
    list_filter = ("is_active", "base_currency")
    search_fields = ("name", "slug", "tax_number")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "role", "is_default", "created_at")
    list_filter = ("company", "role", "is_default")
    search_fields = ("user__username", "user__email", "company__name")
    autocomplete_fields = ("user", "company")
    ordering = ("company", "user")


class IndividualProfileInline(admin.StackedInline):
    model = IndividualProfile
    can_delete = False
    extra = 0


class OrganizationProfileInline(admin.StackedInline):
    model = OrganizationProfile
    can_delete = False
    extra = 0


@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ("display_name", "type", "company", "email", "phone", "is_active", "created_at")
    list_filter = ("company", "type", "is_active")
    search_fields = ("display_name", "email", "phone")
    autocomplete_fields = ("company",)
    inlines = [IndividualProfileInline, OrganizationProfileInline]
    ordering = ("company", "display_name")


    def get_inline_instances(self, request, obj=None):
        inlines = super().get_inline_instances(request, obj)
        if obj and obj.type == Entity.EntityType.INDIVIDUAL:
            return [inline for inline in inlines if isinstance(inline, IndividualProfileInline)]
        elif obj and obj.type == Entity.EntityType.ORGANIZATION:
            return [inline for inline in inlines if isinstance(inline, OrganizationProfileInline)]
        return inlines


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("company", "code", "name", "customer", "start_date", "end_date", "is_active")
    list_filter = ("company", "is_active")
    search_fields = ("code", "name", "customer__display_name")
    autocomplete_fields = ("company", "customer")
    ordering = ("company", "code")