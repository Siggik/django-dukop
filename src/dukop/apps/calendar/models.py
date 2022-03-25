import calendar
import os
import random
import string
import uuid
from builtins import staticmethod
from datetime import datetime
from functools import lru_cache

from django.contrib.sites.models import Site
from django.core.cache import cache
from django.db import models
from django.db import transaction
from django.db.models import Q
from django.template.defaultfilters import truncatewords
from django.urls.base import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from dukop.apps.calendar.utils import display_datetime
from dukop.apps.calendar.utils import display_time
from dukop.apps.calendar.utils import timedelta_fixed_time
from sorl.thumbnail import get_thumbnail

from . import utils


def image_upload_to(instance, filename):
    ext = filename.split(".")[-1]
    filename = "%s.%s" % (uuid.uuid4(), ext)
    return os.path.join("uploads/events", filename)


def sluggify_instance(instance, ModelClass, name_field, slug_field):
    """
    Auto-populates a slug field if it isn't filled in.
    """
    if not instance.pk and not getattr(instance, slug_field, None):
        proposal = slugify(getattr(instance, name_field))[:50]

        def _proposal_exists():
            return ModelClass.objects.filter(**{slug_field: proposal}).exists()

        proposal_exists = _proposal_exists()
        while proposal_exists:
            to_append = "".join(
                random.choice(string.ascii_uppercase + string.digits) for _ in range(10)
            )
            proposal = proposal[:40] + to_append
            proposal_exists = _proposal_exists()
        setattr(instance, slug_field, proposal)


class EventQuerySet(models.QuerySet):
    def active(self):
        """Returns queryset of active events"""
        return self.filter(published=True, deleted=False)

    def future(self, truncate_time_today=True):
        """
        Selects all events that start in the future or haven't yet finished
        """
        if truncate_time_today:
            now = utils.get_now().replace(minute=0, hour=0, second=0)
        else:
            now = utils.get_now()
        return self.filter(Q(times__start__gte=now) | Q(times__end__gte=now)).distinct()

    def past(self, truncate_time_today=True):
        """
        Selects all irrelevant events, i.e. events that have ended
        """
        if truncate_time_today:
            now = utils.get_now().replace(minute=0, hour=0, second=0)
        else:
            now = utils.get_now()
        return self.filter(
            Q(times__start__lt=now) & (Q(times__end__lt=now) | Q(times__end=None))
        ).distinct()


class EventManager(models.Manager):
    def get_queryset(self):
        return (
            EventQuerySet(self.model, using=self._db)
            .prefetch_related("times")
            .prefetch_related("images")
        )

    def active(self):
        return self.get_queryset().active()

    def future(self):
        return self.get_queryset().future()

    def past(self):
        return self.get_queryset().past()


class EventTimeQuerySet(models.QuerySet):
    def future(self, truncate_time_today=True):
        """
        Selects all events that start in the future or haven't yet finished
        """
        if truncate_time_today:
            now = utils.get_now().replace(minute=0, hour=0, second=0)
        else:
            now = utils.get_now()
        return self.filter(Q(start__gte=now) | Q(end__gte=now))

    def past(self, truncate_time_today=True):
        """
        Selects all irrelevant events, i.e. events that have ended
        """
        if truncate_time_today:
            now = utils.get_now().replace(minute=0, hour=0, second=0)
        else:
            now = utils.get_now()
        return self.filter(Q(start__lt=now) & (Q(end__lt=now) | Q(end=None)))

    def active(self):
        """Returns EventTime queryset of active events"""
        return self.filter(event__published=True, event__deleted=False)


class EventTimeManager(models.Manager):
    def get_queryset(self):
        return EventTimeQuerySet(self.model, using=self._db)

    def future(self, truncate_time_today=True):
        return self.get_queryset().future(truncate_time_today=truncate_time_today)

    def past(self, truncate_time_today=True):
        return self.get_queryset().past(truncate_time_today=truncate_time_today)

    def active(self):
        return self.get_queryset().active()


class Sphere(models.Model):
    """
    Spheres are local versions of a site containing sets of events. Over time,
    they may change and define their own themes, priorities etc. We don't know.
    """

    name = models.CharField(max_length=255)

    slug = models.SlugField(
        null=True,
        blank=True,
        verbose_name=_("slug"),
        help_text=_("The part of a URL that is displayed in dukop.dk/sphere/<slug>/"),
    )

    default = models.BooleanField(default=False)

    admins = models.ManyToManyField(
        "users.User",
        limit_choices_to={"is_staff": True},
    )

    sub_spheres = models.ManyToManyField(
        "self",
        verbose_name=_("Related spheres"),
        blank=True,
        help_text=_(
            "Other spheres intersecting or contained within this sphere. This can only have one level of 'nested' spheres - you can only choose spheres that aren't also containing other spheres."
        ),
        limit_choices_to={"sub_spheres": None},
        related_name="metaspheres",
        symmetrical=False,
    )

    class Meta:
        ordering = ("-default", "name")
        verbose_name = _("Sphere")
        verbose_name_plural = _("Spheres")

    def save(self, *args, **kwargs):
        sluggify_instance(self, Sphere, "name", "slug")
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @staticmethod
    def get_default():
        """
        This can be cached in-memory insofar that we don't do any more funky
        stuff with the Spheres, like related querysets etc.
        """
        try:
            return Sphere.objects.get(default=True)
        except Sphere.DoesNotExist:
            return Sphere.objects.create(
                name="Auto-created sphere", slug="auto", default=True
            )

    @staticmethod
    def get_default_cached():
        """
        This can be cached in-memory insofar that we don't do any more funky
        stuff with the Spheres, like related querysets etc.
        """
        if getattr(Sphere, "_cached_default", None):
            return Sphere._cached_default
        else:
            Sphere._cached_default = Sphere.get_default()
            return Sphere._cached_default

    @staticmethod
    def get_all_cached():
        """
        This can be cached in-memory insofar that we don't do any more funky
        stuff with the Spheres, like related querysets etc.
        """
        spheres = cache.get("dukop_all_spheres", None)
        if not spheres:
            spheres = list(Sphere.objects.all().order_by("default"))
            cache.set("dukop_all_spheres", spheres)

        return spheres

    @staticmethod
    def get_by_id_or_default(sphere_id=None):
        """
        Fetches a sphere by its ID or returns the default sphere
        """
        if not sphere_id:
            return Sphere.get_default()
        try:
            return Sphere.objects.get(pk=sphere_id)
        except Sphere.DoesNotExist:
            return Sphere.get_default()

    @staticmethod
    @lru_cache(maxsize=128)
    def get_by_id_or_default_cached(sphere_id=None):
        """
        Fetches a sphere by its ID or returns the default sphere
        """
        return Sphere.get_by_id_or_default(sphere_id=sphere_id)


class Event(models.Model):
    """
    Recurrence:

    An event can be ascribed as many EventTime instances as necessary to express
    recurrence.

    Once in a while, we need to maintain this information, though. But we do not
    auto-create EventTime objects way into the future - there is no need for
    that.

    Calendars have "Edit this occurrence" or "Edit all occurrences"

    Likewise, we also need a way for events that have occurred to remain
    untouched, while future events can be edited.

    https://github.com/bmoeskau/Extensible/blob/master/recurrence-overview.md
    """

    spheres = models.ManyToManyField(
        Sphere,
        blank=True,
    )

    name = models.CharField(
        max_length=255,
        verbose_name=_("name"),
    )
    short_description = models.TextField(
        blank=True,
        verbose_name=_("short description"),
        help_text=_(
            "A special short version of the event description, leave blank to auto-generate."
        ),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("description"),
        help_text=_("Enter details, which will be displayed on the event's own page."),
    )

    slug = models.SlugField(
        null=True,
        blank=True,
        verbose_name=_("slug"),
        help_text=_("The part of a URL that is displayed in dukop.dk/event/<slug>/"),
    )

    host = models.ForeignKey(
        "users.Group",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="events",
        help_text=_(
            "A group may host an event and be displayed as the author of the event text."
        ),
    )

    location = models.ForeignKey(
        "users.Location",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="events_here",
        help_text=_("The location (venue) of the event."),
    )

    featured = models.BooleanField(default=False)
    published = models.BooleanField(default=True)
    deleted = models.BooleanField(default=False)

    online = models.BooleanField(
        default=False,
        verbose_name=_("Online event"),
        help_text=_("Use the Description field to tell users how to join or sign up."),
    )
    location_tba = models.BooleanField(default=False, verbose_name=_("TBA"))

    is_cancelled = models.BooleanField(default=False)

    venue_name = models.CharField(
        max_length=255,
        verbose_name=_("venue name"),
        blank=True,
        null=True,
    )
    street = models.CharField(
        max_length=255,
        verbose_name=_("street"),
        blank=True,
        null=True,
    )
    city = models.CharField(
        max_length=255,
        verbose_name=_("city"),
        blank=True,
        null=True,
    )
    zip_code = models.CharField(
        verbose_name=_("zip code"),
        blank=True,
        null=True,
        max_length=16,
    )

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    deleted_on = models.DateTimeField(null=True, blank=True, editable=False)

    owner_user = models.ForeignKey(
        "users.User",
        verbose_name=_("owner (user)"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_events",
    )
    owner_group = models.ForeignKey(
        "users.Group",
        verbose_name=_("owner (group)"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_events",
    )

    edit_secret = models.CharField(
        max_length=255,
        verbose_name=_("edit secret"),
        blank=True,
        null=True,
        editable=False,
    )

    view_secret = models.CharField(
        max_length=255,
        verbose_name=_("view secret"),
        blank=True,
        null=True,
        editable=False,
    )

    objects = EventManager()

    class Meta:
        verbose_name = _("Event")

    def save(self, *args, **kwargs):
        """
        Auto-populates the slug field if it isn't filled in.
        """
        sluggify_instance(self, Event, "name", "slug")
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def share_link(self):
        current_site = Site.objects.get_current()
        domain = current_site.domain
        return "https://{}{}".format(
            domain, reverse("calendar:event_detail", kwargs={"pk": self.pk})
        )

    def get_display_host(self):
        if self.host:
            return self.host.name
        if self.owner_user:
            return self.owner_user.get_display_name()
        return _("Unspecified host")

    def get_short_description(self):
        """
        Fetches a short description of the event.
        """
        if not self.short_description:
            return truncatewords(self.description, 100)
        return self.short_description

    @property
    def venue(self):
        if self.host:
            return self.host.name
        elif self.venue_name:
            return self.venue_name
        return _("Unspecified")

    def can_edit(self, user):
        if user.is_superuser:
            return True
        if self.owner_user == user:
            return True
        return False


class EventTime(models.Model):
    """
    Allows an event to take place at many different times
    """

    event = models.ForeignKey(Event, related_name="times", on_delete=models.CASCADE)
    start = models.DateTimeField(
        verbose_name=_("start"),
    )
    end = models.DateTimeField(
        verbose_name=_("end"),
        blank=True,
        null=True,
    )
    comment = models.CharField(
        max_length=255,
        verbose_name=_("comment"),
        help_text=_("Leave blank and nothing will be shown to readers"),
        blank=True,
        null=True,
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    is_cancelled = models.BooleanField(default=False)

    recurrence = models.ForeignKey(
        "EventRecurrence",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("recurrence"),
        help_text=_("Belonging to a recurring recurrence"),
        related_name="times",
    )
    #: This can be switched to False and if the EventTime belongs to an
    #: EventRecurrence, it will not be maintained automatically anymore.
    #: This allows for individual changes.
    recurrence_auto = models.BooleanField(
        default=False,
        verbose_name=_("automatic recurrence"),
        help_text=_(
            "If true, this recurrence is currently maintained automatically and "
            "has not been rescheduled. If the recurrence is edited, it may be "
            "changed automatically"
        ),
    )

    objects = EventTimeManager()

    #: An exception to the event's general description in case there are several EventTime instances for the same Event
    description = models.TextField(
        blank=True,
        verbose_name=_("description"),
        help_text=_(
            "Leave blank to use the general event's description. If filled in, will be displayed together when a user navigates to this specific occurrence of the event."
        ),
    )

    class Meta:
        verbose_name = _("Event time")
        ordering = ("start", "end")

    def __str__(self):
        representation = display_datetime(self.start)
        if self.end:
            if self.end.date() == self.start.date():
                representation += " - {}".format(display_time(self.end))
            else:
                representation += " - {}".format(display_datetime(self.end))
        return representation


class EventUpdate(models.Model):
    """
    An update can be posted by event owners and will be visible on the event
    page for users to see.
    """

    event = models.ForeignKey(Event, related_name="updates", on_delete=models.CASCADE)

    description = models.TextField(
        blank=True,
        verbose_name=_("description"),
    )

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Event update")
        ordering = ("created",)


class EventImage(models.Model):

    event = models.ForeignKey(Event, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(
        verbose_name=_("image"),
        help_text=_(
            "Allowed formats: JPEG, PNG, GIF. Please upload high resolution (>1000 pixels wide)."
        ),
        upload_to=image_upload_to,
    )
    priority = models.PositiveSmallIntegerField(
        default=0, help_text=_("0=first, 1=second etc.")
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("priority",)

    def thumb(self, width=100, height=75):
        try:
            return get_thumbnail(
                self.image.file,
                "{}x{}".format(width, height),
                crop="center",
                quality=90,
            )
        except OSError as e:
            if "RGBA" in str(e):
                return get_thumbnail(
                    self.image.file,
                    "{}x{}".format(width, height),
                    crop="center",
                    format="PNG",
                )
            else:
                raise


class EventLink(models.Model):
    """
    Links have automatically generated labels, in this way we can
    potentially translate them or make them consistent. For instance,
    we can make Facebook links display with a warning.
    """

    event = models.ForeignKey(Event, related_name="links", on_delete=models.CASCADE)
    link = models.URLField(
        blank=True,
        null=True,
        max_length=2048,
        help_text=_("Must begin with 'https://' or 'http://'"),
    )
    priority = models.PositiveSmallIntegerField(
        default=0, help_text=_("0=first, 1=second etc.")
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("priority", "link")


class EventRecurrence(models.Model):
    """
    Inspired by RRULE for iCal format:

    https://www.kanzaki.com/docs/ical/rrule.html
    """

    #: A series is based on an event and an anchored EventTime, which is then
    #: repeated in the recurrence. This means that we have the flexibility to
    #: have several recurrences for the same event.
    event = models.ForeignKey(
        Event, related_name="recurrences", on_delete=models.CASCADE
    )

    #: In order to duplicate an event, we need to start with the first time slot
    #: which is then duplicated. Afterwards, it might be edited separately, so
    #: this field is only useful for populating an EventRecurrence the first time.
    #: For weekly events, the anchor decides the weekday.
    event_time_anchor = models.ForeignKey(
        EventTime,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="recurrence_anchors",
    )

    #: List of types of recurrences that users can choose.
    RECURRENCE_TYPES = [
        ("every_week", _("Weekly")),
        ("biweekly_even", _("Even weeks")),
        ("biweekly_odd", _("Odd weeks")),
        ("first_week_of_month", _("First week of month")),
        ("second_week_of_month", _("Second week of month")),
        ("third_week_of_month", _("Third week of month")),
        ("last_week_of_month", _("Last week of month")),
    ]

    # Notice how these recurrences intersect. The really hard part occurs when
    # an recurrence changes it recurrence. You can't say if an existing "every_week"
    # recurrence is supposed to be the same as a new set of "last_week_of_month".
    every_week = models.BooleanField(default=False)
    biweekly_even = models.BooleanField(default=False)
    biweekly_odd = models.BooleanField(default=False)
    first_week_of_month = models.BooleanField(default=False)
    second_week_of_month = models.BooleanField(default=False)
    third_week_of_month = models.BooleanField(default=False)
    last_week_of_month = models.BooleanField(default=False)

    #: The end time of an recurrence gives us an upper bound so occurences aren't
    #: created for eternity. If none is supplied, we use a system-default
    #: relative to ``now()``. It should mean ``<``
    end = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("End of series"),
    )

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    @classmethod
    def recurrence_type_static(cls, obj):
        if isinstance(obj, dict):
            # A dictionary
            for type_id, __ in cls.RECURRENCE_TYPES:
                if obj.get(type_id, False):
                    return type_id
        # A normal model instance w/ attributes
        for type_id, __ in cls.RECURRENCE_TYPES:
            if getattr(obj, type_id, False):
                return type_id

    @classmethod
    def recurrence_name_static(cls, obj):
        if isinstance(obj, dict):
            # A dictionary
            for type_id, name in cls.RECURRENCE_TYPES:
                if obj.get(type_id, False):
                    return name
        # A normal model instance w/ attributes
        for type_id, name in cls.RECURRENCE_TYPES:
            if getattr(obj, type_id, False):
                return name

    @property
    def recurrence_type(self):
        return self.recurrence_type_static(self)

    @property
    def recurrence_name(self):
        return self.recurrence_name_static(self)

    @method_decorator(transaction.atomic)
    def sync(self, maximum=180, create_old_times=False):
        """
        This is in a transaction.

        Stupid examples of things that are annoying:

        - Editing the weekday of a recurrence, what to do with existing EventTimes!?
        - Editing the recurrence frequency

        Creates the necessary EventTime objects for an Event.
        That is to say: Given a "main" or "prototype" event, populate a series
        of copied EventTime for some maximum, respecting
        """
        if create_old_times:
            start = self.event_time_anchor.start
        else:
            tz = timezone.get_current_timezone()
            start = max(
                tz.localize(
                    datetime.combine(
                        utils.get_now().date(),
                        timezone.localtime(self.event_time_anchor.start).time(),
                    )
                ),
                self.event_time_anchor.start,
            )

        existing_times = {
            et.start.date(): et
            for et in self.times.filter(
                recurrence_auto=True, start__date__gte=start.date()
            )
        }
        updated_times = []
        for event_time in self.event_time_generator(start, maximum, existing_times):
            event_time.save()
            updated_times.append(event_time)

        # Delete everything that existed before but is not part of this generated series
        for et in existing_times.values():
            if et not in updated_times:
                et.delete()

    def event_time_generator(  # noqa: max-complexity: 16
        self, start, maximum, existing_times
    ):
        """A generator that yields new EventTime objects (unsaved)"""
        assert self.event_time_anchor, "Needs event_time_anchor (the first occurrence)"

        # Yield the anchor EventTime object through the update_or_add_to_recurrence
        # method, thus ensuring its validity for this recurrence.
        if start.date() <= self.event_time_anchor.start.date():
            yield self.update_or_add_to_recurrence(
                existing_times, event_time=self.event_time_anchor
            )

        # The end of the recurrence, either as given by an explicit user-defined
        # end datetime or as a number of days relative to the start of the
        # recurrence.
        system_wide_maximum = timedelta_fixed_time(start, days=maximum).date()
        end = self.end or system_wide_maximum

        end = timezone.make_aware(
            datetime.combine(min(end, system_wide_maximum), datetime.min.time())
        )

        # We store the duration of the anchor event in order to create dynamic
        # end times of each EventTime in the recurrence.
        if self.event_time_anchor.end:
            duration = self.event_time_anchor.end - self.event_time_anchor.start
        else:
            duration = None

        if self.every_week:
            for event_time_start, event_time_end in self._every_week_generator(
                start, end, duration
            ):
                yield self.update_or_add_to_recurrence(
                    existing_times, event_time_start, event_time_end
                )

        else:
            if self.biweekly_even or self.biweekly_odd:
                for event_time_start, event_time_end in self._biweekly_generator(
                    start, end, duration, even_not_odd=self.biweekly_even
                ):
                    yield self.update_or_add_to_recurrence(
                        existing_times, event_time_start, event_time_end
                    )

            if self.first_week_of_month:
                for event_time_start, event_time_end in self._monthly_generator(
                    start, end, duration, offset_weeks=0
                ):
                    yield self.update_or_add_to_recurrence(
                        existing_times, event_time_start, event_time_end
                    )
            if self.second_week_of_month:
                for event_time_start, event_time_end in self._monthly_generator(
                    start, end, duration, offset_weeks=1
                ):
                    yield self.update_or_add_to_recurrence(
                        existing_times, event_time_start, event_time_end
                    )
            if self.third_week_of_month:
                for event_time_start, event_time_end in self._monthly_generator(
                    start, end, duration, offset_weeks=2
                ):
                    yield self.update_or_add_to_recurrence(
                        existing_times, event_time_start, event_time_end
                    )
            if self.last_week_of_month:
                for (
                    event_time_start,
                    event_time_end,
                ) in self._last_day_of_month_generator(start, end, duration):
                    yield self.update_or_add_to_recurrence(
                        existing_times, event_time_start, event_time_end
                    )

    def update_or_add_to_recurrence(
        self,
        existing_times,
        event_time_start=None,
        event_time_end=None,
        event_time=None,
    ):
        """
        Updates an existing event_time in series, but if none exists, we
        create a new object.
        """
        assert event_time_start or event_time
        if event_time_start:
            if event_time_start.date() in existing_times:
                event_time = existing_times[event_time_start.date()]
            else:
                event_time = EventTime(event=self.event)
                event_time.start = event_time_start
                event_time.end = event_time_end
        event_time.recurrence = self
        event_time.recurrence_auto = True
        return event_time

    def _every_week_generator(self, start, end, duration):
        current_start = timedelta_fixed_time(start, days=7)
        while current_start < end:
            current_end = current_start + duration if duration else None
            yield current_start, current_end
            current_start = timedelta_fixed_time(current_start, days=7)

    def _biweekly_generator(self, start, end, duration, even_not_odd=True):
        current_start = start
        __, week, __ = current_start.date().isocalendar()

        # We account for a case where the anchor date is in fact NOT the same
        # even/odd week number of the series.
        if week % 2 != (0 if even_not_odd else 1):
            current_start = timedelta_fixed_time(current_start, days=7)
        else:
            current_start = timedelta_fixed_time(current_start, days=14)
        while current_start < end:
            current_end = current_start + duration if duration else None
            yield current_start, current_end
            current_start = timedelta_fixed_time(current_start, days=14)

    def _monthly_generator(self, start, end, duration, offset_weeks=0):
        """
        :param: offset_weeks: The number of weeks from the beginning, 0=first week
        """
        current_start = start
        while True:
            if current_start.month == 12:
                first_day_in_month = current_start.replace(
                    year=current_start.year + 1,
                    month=1,
                    day=1,
                )
            else:
                first_day_in_month = current_start.replace(
                    month=current_start.month + 1,
                    day=1,
                )
            offset = (
                self.event_time_anchor.start.weekday() - first_day_in_month.weekday()
            )
            if offset < 0:
                offset += 7
            offset += 7 * offset_weeks
            current_start = first_day_in_month.replace(
                day=1 + offset,
            )
            current_end = current_start + duration if duration else None
            if current_start >= end:
                break
            yield current_start, current_end

    def _last_day_of_month_generator(self, start, end, duration):
        current_start = start
        target_weekday = current_start.weekday()
        while True:
            if current_start.month == 12:
                next_month = 1
                next_year = current_start.year + 1
            else:
                next_month = current_start.month + 1
                next_year = current_start.year
            # The weekday index is different in the "calendar" package so disregard
            __, last_day = calendar.monthrange(next_year, next_month)
            current_start = current_start.replace(
                year=next_year, month=next_month, day=last_day
            )
            last_day_weekday = current_start.weekday()
            diff = target_weekday - last_day_weekday
            if diff > 0:
                diff = -7 + diff
            current_start = current_start.replace(
                day=last_day + diff,
            )
            current_end = current_start + duration if duration else None
            if current_start >= end:
                break
            yield current_start, current_end


class Weekday(models.Model):

    name = models.CharField(
        max_length=255,
        verbose_name=_("name"),
    )
    number = models.PositiveSmallIntegerField(default=0, unique=True)


class OldEventSync(models.Model):

    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    old_fk = models.PositiveIntegerField()
    is_series = models.BooleanField()

    class Meta:
        unique_together = ("old_fk", "is_series")
