from datetime import timedelta

from django import template
from django.contrib.sites.models import Site
from django.db.models import Q
from django.template.defaultfilters import truncatechars
from django.urls.base import reverse
from django.utils.html import linebreaks
from django.utils.safestring import mark_safe
from django.utils.timezone import localtime

from .. import models
from .. import utils

register = template.Library()


@register.simple_tag
def get_event_times(  # noqa: max-complexity=12
    from_date=None,
    to_date=None,
    days=None,
    max_count=100,
    or_featured=False,
    featured=None,
    published=True,
    has_image=None,
    sphere=None,
    host=None,
    location=None,
    hide_recurring=False,
):

    lookups = [Q(event__published=published)]

    if sphere:
        lookups.append(
            Q(Q(event__spheres=sphere) | Q(event__spheres__metaspheres=sphere))
        )

    if from_date == "today":
        from_date = utils.get_now().replace(minute=0, hour=0, second=0)
    elif from_date == "future":
        from_date = utils.get_now()
    else:
        from_date = utils.get_now().replace(minute=0, hour=0, second=0)

    if days:
        to_date = from_date + timedelta(days=days)

    if from_date:
        lookups.append((Q(start__gte=from_date) & Q(end=None)) | Q(end__gte=from_date))

    if or_featured:
        if to_date:
            lookups.append(Q(start__lte=to_date) | Q(event__featured=True))
    else:
        if to_date:
            lookups.append(Q(start__lte=to_date))

    if featured is not None:
        lookups.append(Q(event__featured=bool(featured)))

    if host is not None:
        lookups.append(Q(event__host=host))

    if location is not None:
        lookups.append(Q(event__location=location))

    if hide_recurring:
        lookups.append(Q(recurrence=None))

    if has_image is not None:
        if has_image:
            lookups.append(Q(event__images__id__gte=0))
        else:
            lookups.append(Q(event__images=None))

    return (
        models.EventTime.objects.filter(*lookups)
        .select_related("event")
        .prefetch_related("event__images", "event__links")
    ).distinct()[:max_count]


@register.simple_tag
def event_timeline_properties(event_time, now=None):
    """
    Properties to be used by the timeline filter
    """

    if not now:
        now = localtime(utils.get_now())

    hours_x_min = 8
    hours_x_max = 24
    hours_x = hours_x_max - hours_x_min

    start = localtime(event_time.start)
    end = localtime(event_time.end) if event_time.end else None

    if start.date() < now.date() or start.hour < hours_x_min:
        x_start = hours_x_min
    else:
        x_start = start.hour + (start.minute / 60.0)

    if not end:
        x_end = x_start
    elif end.date() > now.date() or end.hour >= hours_x_max:
        x_end = hours_x_max
    else:
        x_end = end.hour + (end.minute / 60.0)

    x_start_pct = 100.0 * float(x_start - hours_x_min) / hours_x
    x_end_pct = 100.0 * float(x_end - hours_x_min) / hours_x

    width_pct = x_end_pct - x_start_pct

    return {
        "x_start_pct": x_start_pct,
        "x_end_pct": x_end_pct,
        "width_pct": width_pct,
    }


@register.filter_function
def dukop_date(dtm):
    return utils.display_date(dtm)


@register.filter_function
def dukop_time(dtm):
    return utils.display_time(dtm)


@register.filter_function
def dukop_datetime(dtm):
    return utils.display_datetime(dtm)


@register.filter_function
def dukop_interval(start, end=None):
    """
    Displays an interval, e.g. "2021-04-02 15:00-16:00"
    """
    return utils.display_interval(start, end)


@register.simple_tag
def feed_link(feed_url, **kwargs):
    """
    Takes a resolvable view name and returns a full path, i.e. calendar:feed_rss
    """
    current_site = Site.objects.get_current()
    domain = current_site.domain
    return "https://{}{}".format(domain, reverse(feed_url, kwargs=kwargs))


@register.filter
def url_alias(url):
    """
    Turns for instance "https://mastodon.org/blah/blah" into "mastodon.org"
    """

    try:
        __, domain_path = url.split("://")
        domain = domain_path.split("/")[0]
        domain = domain.strip("www.")
        if domain == "facebook.com":
            domain = "facebook.com (which tracks you)"
        return domain
    except (IndexError, ValueError):
        return "Invalid URL"


@register.filter
def event_can_edit(event, user):
    return event.can_edit(user)


@register.filter
@mark_safe
def event_description(event, truncate=100):
    truncated_description = ""
    if event.description:
        truncated_description = truncatechars(event.description, truncate)
    else:
        truncated_description = truncatechars(event.short_description, truncate)

    return linebreaks(truncated_description)


@register.filter
def recurrence_interval(recurrence_like_obj):
    return models.EventRecurrence.recurrence_name_static(recurrence_like_obj)
