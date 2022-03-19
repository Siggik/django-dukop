from datetime import datetime
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext as _


def get_now():
    """
    This is the central function for determining what's past and present in the
    eyes of any function in the calendar. It is used to mimic the past in
    testing and development.
    """
    now = timezone.localtime()
    if hasattr(settings, "DUKOP_BACKWARDS_DAYS"):
        return now - timedelta(days=settings.DUKOP_BACKWARDS_DAYS)
    return now


def display_date(dtm):
    return date_format(dtm)


def display_time(dtm):
    return timezone.localtime(dtm).strftime("%H:%M")


def display_datetime(dtm):
    return _("{date} at {time}").format(date=date_format(dtm), time=display_time(dtm))


def display_interval(start, end=None, line_break=False):
    """
    Displays an interval, something with a start and finish. Since having a
    finish isn't mandatory, it may be omitted silently.

    This can be made even more elegant.

    Remember that when changing formats, translations have to be updated, too.

    :param: line_break: Adds a linebreak in case the end date contains a date and time.
    """
    if not end:
        return _("{start_date} at {start_time}").format(
            start_date=date_format(start), start_time=display_time(start)
        )
    elif end.date() == start.date():
        return _("{start_date} at {start_time} - {end_time}").format(
            start_date=date_format(start),
            start_time=display_time(start),
            end_time=display_time(end),
        )
    else:
        return _("{start_date} at {start_time}{br} to {end_date} at {end_time}").format(
            start_date=date_format(start),
            end_date=date_format(end),
            start_time=display_time(start),
            end_time=display_time(end),
            br="<br>" if line_break else "",
        )


def timedelta_fixed_time(dtm1, **kwargs):
    """
    Fixates the time - meaning that if you add 7 days to any timestamp, it will
    firstly apply the current timezone according to your Django settings
    """
    tz = timezone.get_current_timezone()
    # Firstly, force dtm1 to be in the local timezone (tzinfo), because otherwise
    # it might be for instance represented as UTC. What we want to achieve is
    # to keep the time() of the original timestamp, regardless of the DST changes
    # that can occur in the interval that the date is pushed.
    localized_dtm1 = timezone.localtime(dtm1, tz)
    return tz.localize(
        (
            datetime.combine(
                localized_dtm1.date() + timedelta(**kwargs), localized_dtm1.time()
            )
        )
    )
