import pytz
from django.contrib.syndication.views import Feed
from django.shortcuts import get_object_or_404
from django.urls.base import reverse
from django.utils import feedgenerator
from django.utils.feedgenerator import rfc2822_date
from django.utils.translation import gettext as _
from django_ical.views import ICalFeed
from PIL import Image
from sorl.thumbnail.shortcuts import get_thumbnail

from . import models


class EventFeed(ICalFeed):
    """
    A simple event calender
    """

    product_id = "-//dukop.dk//Kalender"
    timezone = "UTC"
    file_name = "dukop.ics"

    def get_object(self, request, *args, **kwargs):
        """
        This gets the primary object that the feed revolves around. For instance:
         * A venue
         * A sphere
         * A group
         * etc...
        """
        self.request = request
        sphere_id = kwargs.get("sphere_id")
        if sphere_id:
            return get_object_or_404(models.Sphere, pk=sphere_id)
        return None

    def file_name(self, obj):
        if obj:
            return "{}.ics".format(obj.slug)

    def title(self, obj):
        if obj:
            return _("Duk Op calendar for {}".format(obj.name))
        else:
            return _("Duk Op future events")

    def items(self, obj):
        event_times = models.EventTime.objects.active()
        if obj:
            event_times = event_times.filter(event__spheres=obj)
        return event_times.future()

    def item_link(self, item):
        return item.event.share_link()

    def item_title(self, item):
        return item.event.name

    def item_description(self, item):
        return item.event.short_description + _("\n\nRead more: {}").format(
            self.item_link(item)
        )

    def item_start_datetime(self, item):
        return item.start.astimezone(pytz.timezone("UTC"))

    def item_end_datetime(self, item):
        return item.end.astimezone(pytz.timezone("UTC"))

    def item_location(self, item):
        location = item.event.venue_name or ""
        if item.event.street:
            location += "\n" + item.event.street
        if item.event.city:
            location += "\n" + item.event.city
        if item.event.zip_code:
            location += " " + item.event.zip_code
        return location


class EventFeedDetail(EventFeed):
    """
    Fetches just 1 event by PK
    """

    def get_object(self, request, *args, **kwargs):
        self.event_id = kwargs.get("event_id")
        self.event = get_object_or_404(models.Event.objects.active(), id=self.event_id)
        return super().get_object(request, *args, **kwargs)

    def file_name(self, obj):
        return "{}.ics".format(self.event.slug)

    def items(self, obj):
        event_times = super().items(obj)
        event_times = event_times.filter(event=self.event)
        return event_times


class DukOpEventRssGenerator(feedgenerator.Rss201rev2Feed):
    def add_item_elements(self, handler, item):
        super().add_item_elements(handler, item)
        handler.addQuickElement("start_datetime", str(item["start_datetime"]))


class RssFeed(Feed):
    """
    TODO: This feed should specify a Sphere using get_object etc.
    """

    feed_type = DukOpEventRssGenerator
    description_template = "calendar/feeds/future.html"

    def get_object(self, request, *args, **kwargs):
        """
        This gets the primary object that the feed revolves around. For instance:
         * A venue
         * A sphere
         * A group
         * etc...
        """
        self.request = request
        sphere_id = kwargs.get("sphere_id")
        if sphere_id:
            return get_object_or_404(models.Sphere, pk=sphere_id)
        return None

    def item_extra_kwargs(self, item):
        """
        Return an extra keyword arguments dictionary that is used with
        the `add_item` call of the feed generator.
        """
        return {
            "start_datetime": self.item_start_datetime(item),
            "end_datetime": self.item_end_datetime(item),
            "location": self.item_location(item),
        }

    def get_image_url(self, url):
        return self.request.build_absolute_uri(url)

    def item_enclosures(self, item):
        """
        See: https://stackoverflow.com/questions/60227116/django-rss-feed-add-image-to-description
        """
        images = []
        for image in item.event.images.all():
            img = Image.open(image.image.file)
            fill_color = "#ffffff"
            if img.mode in ("RGBA", "LA"):
                background = Image.new(img.mode[:-1], img.size, fill_color)
                background.paste(img, img.split()[-1])
                img = background
                thumbnail = get_thumbnail(img, "800x800", quality=90, format="JPEG")
            else:
                thumbnail = get_thumbnail(img, "800x800", quality=90)
            images.append(
                feedgenerator.Enclosure(
                    self.get_image_url(thumbnail.url),
                    str(image.image.size),
                    "image/{}".format(thumbnail.name.split(".")[-1]),
                )
            )
        return images

    def title(self):
        return _("Duk Op's next 30 events")

    def description(self, obj):
        """
        obj: Needs to be a Sphere object
        """
        return _("RSS feed of the latest events on Duk Op")

    def items(self, obj):
        event_times = models.EventTime.objects.active()
        if obj:
            event_times = event_times.filter(event__spheres=obj)
        return event_times.future()[:30]

    def feed_url(self):
        return reverse("calendar:feed_rss")

    def feed_guid(self, obj):
        return 1

    def link(self):
        return reverse("calendar:index")

    # COPYRIGHT NOTICE -- One of the following three is optional. The
    # framework looks for them in this order.

    feed_copyright = "CopyLeft"  # Hard-coded copyright notice.

    ttl = 600  # Hard-coded Time To Live.

    def item_link(self, item):
        return item.event.share_link()

    def item_title(self, item):
        return item.event.name

    def item_location(self, item):
        location = item.event.venue_name or ""
        if item.event.street:
            location += "\n" + item.event.street
        if item.event.city:
            location += "\n" + item.event.city
        if item.event.zip_code:
            location += " " + item.event.zip_code
        return location

    def item_author_name(self, item):
        return item.event.get_display_host()

    def item_description(self, item):
        return item.event.short_description

    def item_start_datetime(self, item):
        return rfc2822_date(item.start.astimezone(pytz.timezone("UTC")))

    def item_end_datetime(self, item):
        return (
            rfc2822_date(item.end.astimezone(pytz.timezone("UTC"))) if item.end else ""
        )

    def item_pubdate(self, item):
        """
        Takes an item, as returned by items(), and returns the item's
        pubdate.
        """
        return item.event.created

    def item_categories(self, item):
        """
        TODO: Once we have categories
        """
        return []
