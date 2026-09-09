from django.db import models
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator

# [ISO 8601] used across all apps for time, date and user trail (use TZ)
class TimeStamped(models.Model): 
    created_at = models.DateTimeField(auto_now_add=True) 
    updated_at = models.DateTimeField(auto_now=True) 
    created_by = models.ForeignKey( settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+", ) 

    class Meta: 
        abstract = True

# [ISO 4217] currency table, primarily used to populate dropdown selection
class Currency(models.Model):
    alpha_code      = models.CharField(max_length=3, primary_key=True)
    numeric_code    = models.PositiveSmallIntegerField(unique=True,validators=[MinValueValidator(1),MaxValueValidator(999)])
    minor_unit      = models.PositiveSmallIntegerField(validators=[ MinValueValidator(0), MaxValueValidator(3)])
    name            = models.CharField(max_length=100)
    symbol          = models.CharField(max_length=5, blank=True)

    class Meta:
        verbose_name_plural = "currencies"

    def __str__(self):
        return self.alpha_code

# [ISO 20022] exchange rate tables used in multi-currency support cases
class ExchangeRate(models.Model):
    source_currency = models.ForeignKey(Currency,on_delete=models.PROTECT,related_name="exchange_rates_from")
    target_currency = models.ForeignKey(Currency,on_delete=models.PROTECT,related_name="exchange_rates_to")
    quotation_date = models.DateField()
    rate = models.DecimalField(max_digits=18,decimal_places=8)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source_currency", "target_currency", "quotation_date"],
                name="unique_exchange_rate",
            ),
        ]
        indexes = [
            models.Index(
                fields=["source_currency", "target_currency", "-quotation_date"],
            ),
        ]

# Table used for multi-tenancy support (i.e owned/managed companies), not be be confused with Entity -> Organizations (Customers/Suppliers)
class Company(models.Model):
    name            = models.CharField(max_length=255)
    slug            = models.SlugField(unique=True)
    tax_number      = models.CharField(max_length=50, blank=True)
    base_currency   = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="+")
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering            = ["name"]
        verbose_name_plural = "companies"

    def __str__(self):
        return self.name

# Separates user access per company across all apps
class CompanyOwned(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="%(class)ss")

    class Meta:
        abstract = True

# Used to define user access for multi-tenancy support
class Membership(models.Model):
    class Role(models.TextChoices):
        OWNER       = "OWN", "Owner"
        ACCOUNTANT  = "ACC", "Accountant"
        BOOKKEEPER  = "BKP", "Bookkeeper"
        VIEWER      = "VIE", "Viewer"

    user        = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="memberships")
    company     = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="memberships")
    role        = models.CharField(max_length=3, choices=Role.choices, default=Role.VIEWER)
    is_default  = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "company")]

    @property
    def can_post(self):
        return self.role in (self.Role.OWNER, self.Role.ACCOUNTANT)

    @property
    def can_edit(self):
        return self.role != self.Role.VIEWER

# Used for customers, suppliers, partners, leads etc. Any trade activity entities (do not confuse with Company model)
class Entity(CompanyOwned, TimeStamped):
    class EntityType(models.TextChoices):
        INDIVIDUAL      = "I", "Individual"
        ORGANIZATION    = "O", "Organization"

    type                = models.CharField(max_length=1, choices=EntityType.choices)
    display_name        = models.CharField(max_length=255)         
    email               = models.EmailField(blank=True)
    phone               = models.CharField(max_length=50, blank=True)
    address             = models.TextField(blank=True)          
    is_active           = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    
    @property
    def profile(self):
        if self.type == self.EntityType.INDIVIDUAL:
            return self.individual_profile
        return self.organization_profile


class IndividualProfile(models.Model):
    entity              = models.OneToOneField(Entity,on_delete=models.CASCADE,related_name="individual_profile",primary_key=True,)
    first_name          = models.CharField(max_length=100)
    last_name           = models.CharField(max_length=100)
    date_of_birth       = models.DateField(null=True, blank=True)
    #TODO: complete this


class OrganizationProfile(models.Model):
    entity              = models.OneToOneField(Entity,on_delete=models.CASCADE,related_name="organization_profile",primary_key=True,)
    legal_name          = models.CharField(max_length=255)
    tax_number          = models.CharField(max_length=50, blank=True)
    registration_number = models.CharField(max_length=50, blank=True)
    #TODO: complete this

class Project(CompanyOwned):
    code       = models.CharField(max_length=20)
    name       = models.CharField(max_length=255)
    customer   = models.ForeignKey(Entity, on_delete=models.PROTECT, null=True, blank=True, related_name="projects")
    start_date = models.DateField(null=True, blank=True)
    end_date   = models.DateField(null=True, blank=True)
    is_active  = models.BooleanField(default=True)

    class Meta:
        unique_together = [("company", "code")]