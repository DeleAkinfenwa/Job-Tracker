from django.contrib import admin

from .models import AgentRun, CareerEntry, CareerProfile


@admin.register(CareerProfile)
class CareerProfileAdmin(admin.ModelAdmin):
    list_display = ("owner", "updated_at")


@admin.register(CareerEntry)
class CareerEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "entry_date", "role", "source")
    list_filter = ("role", "source")
    search_fields = ("raw_text",)


@admin.register(AgentRun)
class AgentRunAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "kind", "job_title", "ok", "input_tokens", "output_tokens", "created_at")
    list_filter = ("kind", "ok")
