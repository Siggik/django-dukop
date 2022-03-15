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
    path("", views.IndexView.as_view(), name="index"),
    path("group/<int:pk>/", views.GroupDetailView.as_view(), name="group_detail"),
    path(
        "location/<int:pk>/", views.LocationDetailView.as_view(), name="location_detail"
    ),
    path("events/", views.EventListView.as_view(), name="event_list"),
    path("events/dashboard/", views.EventDashboard.as_view(), name="event_dashboard"),
    path("event/<int:pk>/", views.EventDetailView.as_view(), name="event_detail"),
    path(
        "event/<int:pk>/<int:time_pk>/",
        views.EventDetailView.as_view(),
        name="event_detail",
    ),
    path(
        "event/update/<int:pk>/", views.EventUpdateView.as_view(), name="event_update"
    ),
    path(
        "event/update/<int:pk>/images/",
        views.EventImagesUpdateView.as_view(),
        name="event_images_update",
    ),
    path(
        "event/cancel/<int:pk>/", views.EventCancelView.as_view(), name="event_cancel"
    ),
    path(
        "event/publish/<int:pk>/",
        views.EventPublishView.as_view(),
        name="event_publish",
    ),
    path(
        "event/delete/<int:pk>/",
        views.EventDeleteView.as_view(),
        name="event_delete",
    ),
    path("event/create/", views.EventCreateView.as_view(), name="event_create"),
    path(
        "event/<slug:slug>/<int:pk>/",
        views.EventDetailView.as_view(),
        name="event_detail",
    ),
    path(
        "event/<slug:slug>/<int:pk>/",
        views.EventDetailView.as_view(),
        name="event_detail",
    ),
    path(
        "event/<slug:slug>/<int:pk>/<int:time_pk>/",
        views.EventDetailView.as_view(),
        name="event_detail",
    ),
    path("feeds/", views.FeedInstructionView.as_view(), name="feeds"),
    path("feed/ical/", feeds.EventFeed(), name="feed_ical"),
    path("feed/rss/", feeds.RssFeed(), name="feed_rss"),
    path("feed/sphere/ical/<int:sphere_id>/", feeds.EventFeed(), name="feed_ical"),
    path("feed/sphere/rss/<int:sphere_id>/", feeds.RssFeed(), name="feed_rss"),
    path("sphere/change/<int:pk>/", views.set_sphere_session, name="sphere_change"),
    path("feed/event/<int:event_id>/", feeds.EventFeedDetail(), name="feed_event_ical"),
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
