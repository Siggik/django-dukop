from django.contrib import admin
from dukop.apps.calendar.models import OpeningHours
from dukop.apps.calendar.models import Recurrence

from . import models


class OpeningHoursInline(admin.TabularInline):
    model = OpeningHours
    fields = ["weekday", "opens", "closes"] + [
        x[0] for x in Recurrence.RECURRENCE_TYPES
    ]


@admin.register(models.Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "event_count", "deactivated", "is_restricted")
    list_filter = (
        "is_restricted",
        "deactivated",
    )
    search_fields = ("name",)

    def event_count(self, instance):
        return instance.events.all().count()


@admin.register(models.Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "event_count", "deactivated", "is_restricted")
    list_filter = (
        "is_restricted",
        "deactivated",
    )
    search_fields = ("name",)
    inlines = [OpeningHoursInline]

    def event_count(self, instance):
        return instance.events.all().count()


@admin.register(models.User)
class UserAdmin(admin.ModelAdmin):
    pass
