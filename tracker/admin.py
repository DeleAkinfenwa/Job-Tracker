from django.contrib import admin

from .models import Application, Company


# Shows a company's applications inside the company's admin page.
class ApplicationInline(admin.TabularInline):
    model = Application
    extra = 0
    fields = ("role_title", "status", "applied_on", "salary_min", "salary_max")


# Admin list of companies, searchable by name or owner.
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "industry", "location", "created_at")
    list_filter = ("industry",)
    search_fields = ("name", "owner__email")
    inlines = [ApplicationInline]


# Admin list of applications; the stage can be changed straight from the list.
@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("role_title", "company", "owner", "status", "applied_on", "salary_max")
    list_filter = ("status",)
    list_editable = ("status",)
    search_fields = ("role_title", "company__name", "notes")
    date_hierarchy = "applied_on"
    list_select_related = ("company", "owner")
