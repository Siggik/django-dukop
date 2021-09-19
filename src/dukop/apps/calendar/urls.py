from datetime import datetime

from django.urls import path
from django.urls import register_converter
from django.views.i18n import JavaScriptCatalog

from . import feeds
from . import views


class DateConverter:
    regex = r"\d{4}-\d{2}-\d{2}"

    def to_python(self, value):
        return datetime.strptime(value, "%Y-%m-%d").date()

    def to_url(self, value):
        return value


register_converter(DateConverter, "date")


app_name = "calendar"

urlpatterns = [
    path("", views.index, name="index"),
    path("events/", views.EventListView.as_view(), name="event_list"),
    path("events/dashboard/", views.EventDashboard.as_view(), name="event_dashboard"),
    path("event/<int:pk>/", views.EventDetailView.as_view(), name="event_detail"),
    path("event/create", views.EventCreate.as_view(), name="event_create"),
    path(
        "event/create/<int:pk>/",
        views.EventCreateSuccess.as_view(),
        name="event_create_success",
    ),
    path(
        "event/<slug:slug>/<int:pk>/",
        views.EventDetailView.as_view(),
        name="event_detail",
    ),
    path("feeds/", views.FeedInstructionView.as_view(), name="feeds"),
    path("feed/ical/", feeds.EventFeed(), name="feed_ical"),
    path("feed/rss/", feeds.RssFeed(), name="feed_rss"),
    path("feed/sphere/ical/<int:sphere_id>/", feeds.EventFeed(), name="feed_ical"),
    path("feed/sphere/rss/<int:sphere_id>/", feeds.RssFeed(), name="feed_rss"),
    path("sphere/change/<int:pk>/", views.set_sphere_session, name="sphere_change"),
    path(
        "sphere/<int:sphere_id>/events/<date:pivot_date>/",
        views.EventListView.as_view(),
        name="event_list",
    ),
    path(
        "sphere/<int:sphere_id>/events/",
        views.EventListView.as_view(),
        name="event_list",
    ),
    path(
        "jsi18n/",
        JavaScriptCatalog.as_view(packages=["dukop.apps.calendar"]),
        name="javascript-catalog",
    ),
]
