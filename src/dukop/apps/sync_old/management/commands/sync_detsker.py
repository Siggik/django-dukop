"""
Event importing script

Currently unsupported:

- Updating images from old location. They only get created once
- Updating event times
- Updating event links

"""
import os
import sys
import traceback
from datetime import datetime

import pytz
from django.conf import settings
from django.core.files.images import ImageFile
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction
from django.template.defaultfilters import truncatewords
from django.utils import timezone
from dukop.apps.calendar.models import Event
from dukop.apps.calendar.models import EventImage
from dukop.apps.calendar.models import EventLink
from dukop.apps.calendar.models import EventRecurrence
from dukop.apps.calendar.models import EventTime
from dukop.apps.calendar.models import OldEventSync
from dukop.apps.calendar.models import Sphere
from dukop.apps.calendar.models import Weekday
from dukop.apps.news.models import NewsStory
from dukop.apps.sync_old import models
from dukop.apps.users.models import GroupLink
from dukop.apps.users.models import Location


bad_fks = 0


# Gets the number from weekday strings used in old db
weekday_numbers = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}


# Map between old EventSeries and new recurrence
event_series_map = {}

# Maps a single NEW event to its new recurrence
event_recurrence_map = {}


def df(value):
    """
    Converts a UTC non-timezone aware field to current timezone.
    This is because the old system somehow didn't put timezone information
    in datetime fields.
    """
    if not value:
        return None
    return timezone.localtime(
        value.replace(tzinfo=pytz.UTC), pytz.timezone(settings.TIME_ZONE)
    )


def create_recurrence(event_series, new_event, anchor_time):
    """
    Creates an EventRecurrence from old EventSeries object
    """
    if event_series:
        days = event_series.days.split(",")

        for day in days:
            if event_series.rule not in (
                "weekly",
                "biweekly_even",
                "biweekly_odd",
                "first",
                "second",
                "third",
                "last",
            ):
                raise Exception(event_series.rule)
            recurrence = new_event.recurrences.all().first() or EventRecurrence(
                event=new_event
            )
            recurrence.event_time_anchor = anchor_time
            recurrence.weekday = Weekday.objects.get(number=weekday_numbers[day])
            recurrence.every_week = bool(event_series.rule == "weekly")
            recurrence.biweekly_even = bool(event_series.rule == "biweekly_even")
            recurrence.biweekly_odd = bool(event_series.rule == "biweekly_odd")
            recurrence.first_week_of_month = bool(event_series.rule == "first")
            recurrence.second_week_of_month = bool(event_series.rule == "second")
            recurrence.third_week_of_month = bool(event_series.rule == "third")
            recurrence.last_week_of_month = bool(event_series.rule == "last")
            recurrence.start = df(
                datetime.combine(event_series.start_date, event_series.start_time)
            )
            recurrence.end = df(
                datetime.combine(event_series.expiry, event_series.end_time)
            ).date()

            recurrence.save()
            recurrence.sync(create_old_times=True)
            event_recurrence_map[new_event] = recurrence


def ensure_location_exists(old_event):
    global bad_fks
    try:
        if old_event.location and old_event.location.name:
            pass
    except models.Locations.DoesNotExist:
        print("A location had a bad FK")
        bad_fks += 1
        old_event.location = None


def create_location(old_event):
    if not old_event.location or not old_event.location.name:
        return None
    location, created = Location.objects.get_or_create(
        name=old_event.location.name,
        street=old_event.location.street_address,
        zip_code=old_event.location.postcode[:16],
        city=old_event.location.town,
        description=old_event.location.description,
    )
    if created and old_event.location.link:
        GroupLink.objects.create(group=location, link=old_event.location.link)

    return location


def create_event_link(old_event, attach_to_event):
    return EventLink.objects.create(
        event=attach_to_event,
        link=old_event.link,
    )


def create_event(old_event, location, from_event_series=False):

    created = False

    try:
        event = OldEventSync.objects.get(
            is_series=from_event_series, old_fk=old_event.id
        ).event
        print("Event found: {}".format(event.id))
    except OldEventSync.DoesNotExist:
        created = True
        event = Event()

    # This is not a database field
    event.skip_admin_notifications = True

    event.name = old_event.title
    event.short_description = old_event.short_description or ""
    if not event.description:
        event.description = (
            old_event.long_description or old_event.short_description or ""
        )
    event.is_cancelled = bool(old_event.cancelled)
    event.created = df(old_event.created_at)
    event.published = bool(old_event.published)

    if not from_event_series:
        event.featured = bool(old_event.featured)

    event.host = location
    event.location = location

    if old_event.location:
        event.venue_name = old_event.location.name
        event.street = old_event.location.street_address
        event.zip_code = old_event.location.postcode[:16]
        event.city = old_event.location.town
    event.save()
    event.spheres.add(Sphere.objects.get(slug="cph"))
    # event.spheres.add(Sphere.objects.get(default=True))
    OldEventSync.objects.get_or_create(
        is_series=from_event_series,
        old_fk=old_event.id,
        event=event,
    )
    return created, event


def create_event_time(old_event, attach_to_event):
    """
    TODO: Check if it's already created?
    """
    if not old_event.start_time and not old_event.end_time:
        return
    # Don't allow this type of event
    if (old_event.end_time - old_event.start_time).days > 100:
        old_event.end_time = old_event.start_time
    et = EventTime.objects.get_or_create(
        event=attach_to_event,
        start=df(old_event.start_time) or df(old_event.end_time),
        end=df(old_event.end_time) or df(old_event.start_time),
        recurrence=event_recurrence_map.get(attach_to_event, None),
    )[0]
    et.is_cancelled = bool(old_event.cancelled)
    et.description = old_event.long_description or old_event.short_description or ""
    et.created = df(old_event.created_at)
    et.modified = df(old_event.updated_at)
    et.save()
    return et


def create_event_anchor_time(old_event_series, attach_to_event):
    """
    TODO: Check if it's already created?
    """
    assert old_event_series.start_time and old_event_series.end_time
    # The separate date and time are not timezone aware :/
    start = datetime.combine(old_event_series.start_date, old_event_series.start_time)
    end = datetime.combine(old_event_series.start_date, old_event_series.end_time)
    tz = timezone.get_current_timezone()
    return EventTime.objects.create(
        event=attach_to_event,
        recurrence=event_recurrence_map.get(attach_to_event, None),
        start=tz.localize(start),
        end=tz.localize(end),
        created=df(old_event_series.created_at),
        modified=df(old_event_series.updated_at),
        is_cancelled=bool(old_event_series.cancelled),
    )


not_found_images = 0


def import_image(old_event, new_event, old_folder, from_event_series=False):
    """
    TODO: Just skip images that already existed

    Rails has saved images in weird subfolders.
    https://stackoverflow.com/questions/15494906/understanding-id-partition-in-paperclip
    paperclip id_partition method prepend '0' to ID of ActiveRecord instance to make it of length 9 characters.

    i.e 12 would be converted to 000000012, then it simply splits this string into three chunks and joins these chunks with /
    """

    global not_found_images
    subfolders = str(old_event.id).zfill(9)
    subfolders = (
        old_folder,
        "event_series" if from_event_series else "events",
        "pictures",
        subfolders[0:3],
        subfolders[3:6],
        subfolders[6:9],
        "original",
    )
    image_path = os.path.join(
        *subfolders,
        old_event.picture_file_name,
    )
    if os.path.exists(image_path):
        image_data = ImageFile(open(image_path, "rb"))
        event_image = EventImage(event=new_event)
        event_image.image.save("", image_data)
        event_image.save()
        print("Found image {}".format(old_event.picture_file_name))
        return event_image
    else:
        not_found_images += 1
        print(
            "Did not find {}\ntotal images not found: {}".format(
                image_path, not_found_images
            )
        )


def import_event_series(series, import_base_dir):
    global event_series_map
    event = import_event(series, import_base_dir, from_event_series=True)
    event.is_cancelled = series.cancelled
    anchor_time = create_event_anchor_time(series, event)
    # TODO: Why are some cancelled / non-existing series being imported?
    create_recurrence(series, event, anchor_time)
    event_series_map[series.id] = event


def import_event(  # noqa: max-complexity=12
    event, import_base_dir, from_event_series=False
):
    """
    Imports an Event or EventSeries
    """
    global event_series_map
    ensure_location_exists(event)

    # Create a Group from the old Location
    location = create_location(event)

    # Patch up some earlier bad sync'ing by setting this to False here.
    if location:
        location.is_restricted = False

    created = False

    # Create Event
    if (
        from_event_series
        or not event.event_series_id
        or event.event_series_id not in event_series_map
    ):
        created, new_event = create_event(
            event, location, from_event_series=from_event_series
        )
        attach_to_event = new_event
        if created and event.picture_file_name:
            image = import_image(
                event,
                attach_to_event,
                import_base_dir,
                from_event_series=from_event_series,
            )
            if image:
                print(image.image.url)
        if created and event.link:
            create_event_link(event, attach_to_event)
    else:
        attach_to_event = event_series_map[event.event_series_id]

        if not attach_to_event.images.exists() and event.picture_file_name:
            # Only create image if none exist or it's a new event
            if created or not attach_to_event.images.exists():
                image = import_image(event, attach_to_event, import_base_dir)

        new_event = None

    # EventTime
    if attach_to_event and not from_event_series and event.start_time:
        create_event_time(event, attach_to_event)

    if created:
        print("Imported new event: {}".format(new_event))
    elif new_event:
        print("Updated existing event: {}".format(attach_to_event))
    else:
        print("Did not create a new event for old event id {}".format(event.id))

    return new_event


class Command(BaseCommand):
    help = "Import stuff from old database"

    def add_arguments(self, parser):
        # Positional arguments are standalone name
        # parser.add_argument('store_id')

        # Named (optional) arguments start with --
        parser.add_argument(
            "--dry",
            action="store_true",
            default=False,
            help="Dry-run: About the whole database transaction at the end",
        )
        parser.add_argument(
            "import_img_dir",
            type=str,
            help="Base where old images are found",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        global event_series_map

        import_base_dir = options.get("import_img_dir")

        try:
            self.stdout.write("Starting to import")

            # Sync EventSeries
            event_series = models.EventSeries.objects.all()
            for series in event_series:
                self.stdout.write("-----------------------------")
                import_event_series(series, import_base_dir)

            # Sync Events
            events = models.Events.objects.all()
            for event in events:
                self.stdout.write("-----------------------------")
                import_event(event, import_base_dir)

            # Sync news
            for news in models.Posts.objects.all():
                self.stdout.write("-----------------------------")
                self.stdout.write("News: {}".format(news.title))
                story, __ = NewsStory.objects.get_or_create(
                    headline=news.title,
                    short_story=truncatewords(news.body, 100),
                    text=news.body,
                    published=news.featured,
                )
                # Update the auto fields like this
                NewsStory.objects.filter(pk=story.pk).update(
                    created=df(news.created_at),
                    modified=df(news.updated_at),
                )

            self.stdout.write("Command execution completed\n".format())

        except Exception as e:  # noqa
            exc_type, exc_value, exc_traceback = sys.exc_info()
            formatted_excption = traceback.format_exception(
                exc_type, exc_value, exc_traceback
            )
            for line in formatted_excption:
                self.stdout.write(line, ending="")
            raise CommandError(
                "An exception occurred. All operations aborted, database rolled back.\n"
            )

        if options.get("dry"):
            raise CommandError("Dry-running so aborting transactions.")
