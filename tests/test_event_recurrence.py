import calendar

import pytest
from django.utils.timezone import localtime
from dukop.apps.calendar import models
from dukop.apps.calendar.utils import get_now
from dukop.apps.calendar.utils import timedelta_fixed_time

from .fixtures_calendar import single_event  # noqa


# Number of days that an event recurs when no end date is given
default_length_days = 180


@pytest.mark.django_db()
def test_weekdays():
    assert models.Weekday.objects.all().count() > 0


@pytest.mark.django_db()
def test_create_weekly_recurrence(single_event):  # noqa
    """
    Create and test weekly recurrence
    """
    original_weekday = single_event.times.first().start.weekday()
    recurrence = models.EventRecurrence.objects.create(
        event=single_event,
        event_time_anchor=single_event.times.first(),
        every_week=True,
    )
    recurrence.sync()
    # Because the first event is now(), we will always fit 53 events in default_length_days days
    expected_count = default_length_days // 7 + 1
    assert recurrence.times.all().count() == expected_count

    for event_time in recurrence.times.all():
        assert event_time.start.weekday() == original_weekday

    recurrence.sync()
    assert recurrence.times.all().count() == expected_count


@pytest.mark.django_db()
def test_create_biweekly_odd_recurrence(single_event):  # noqa
    """
    Create and test weekly recurrence
    """
    recurrence = models.EventRecurrence.objects.create(
        event=single_event,
        event_time_anchor=single_event.times.first(),
        biweekly_odd=True,
    )
    recurrence.sync()
    assert recurrence.times.first() == single_event.times.first()

    expected_counts = [default_length_days // 14 + 1, default_length_days // 14 + 2]

    assert recurrence.times.all().count() in expected_counts
    recurrence.sync()
    assert recurrence.times.all().count() in expected_counts


@pytest.mark.django_db()
def test_create_biweekly_even_recurrence(single_event):  # noqa
    """
    Create and test weekly recurrence
    """
    recurrence = models.EventRecurrence.objects.create(
        event=single_event,
        event_time_anchor=single_event.times.first(),
        biweekly_even=True,
    )
    recurrence.sync()
    assert recurrence.times.first() == single_event.times.first()

    expected_counts = (
        default_length_days // 14 + 1,
        default_length_days // 14 + 2,
    )

    assert recurrence.times.all().count() in expected_counts
    recurrence.sync()
    assert recurrence.times.all().count() in expected_counts


@pytest.mark.django_db()
def test_create_first_week_of_month_recurrence(single_event):  # noqa
    """
    Create and test weekly recurrence
    """
    original_weekday = single_event.times.first().start.weekday()
    anchor_event_time = single_event.times.first()
    recurrence = models.EventRecurrence.objects.create(
        event=single_event,
        event_time_anchor=anchor_event_time,
        first_week_of_month=True,
    )
    recurrence.sync()

    assert recurrence.times.all().first() == anchor_event_time
    for event_time in recurrence.times.all():
        assert event_time.start.weekday() == original_weekday
        if event_time != anchor_event_time:
            assert event_time.start.day < 8

    expected_counts = [default_length_days // 30, default_length_days // 30 + 1]
    assert recurrence.times.all().count() in expected_counts
    recurrence.sync()
    assert recurrence.times.all().count() in expected_counts


@pytest.mark.django_db()
def test_create_second_week_of_month_recurrence(single_event):  # noqa
    """
    Create and test weekly recurrence
    """
    original_weekday = single_event.times.first().start.weekday()
    anchor_event_time = single_event.times.first()
    recurrence = models.EventRecurrence.objects.create(
        event=single_event,
        event_time_anchor=single_event.times.first(),
        second_week_of_month=True,
    )
    recurrence.sync()

    assert recurrence.times.all().first() == anchor_event_time
    for event_time in recurrence.times.all():
        assert event_time.start.weekday() == original_weekday
        if event_time != anchor_event_time:
            assert event_time.start.day >= 8 < 15

    expected_counts = [default_length_days // 30, default_length_days // 30 + 1]
    assert recurrence.times.all().count() in expected_counts
    recurrence.sync()
    assert recurrence.times.all().count() in expected_counts


@pytest.mark.django_db()
def test_create_third_week_of_month_recurrence(single_event):  # noqa
    """
    Create and test weekly recurrence
    """
    original_weekday = single_event.times.first().start.weekday()
    anchor_event_time = single_event.times.first()
    recurrence = models.EventRecurrence.objects.create(
        event=single_event,
        event_time_anchor=single_event.times.first(),
        third_week_of_month=True,
    )
    recurrence.sync()

    assert recurrence.times.all().first() == anchor_event_time
    for event_time in recurrence.times.all():
        assert event_time.start.weekday() == original_weekday
        if event_time != anchor_event_time:
            assert event_time.start.day >= 14 < 22

    expected_counts = [default_length_days // 30, default_length_days // 30 + 1]
    assert recurrence.times.all().count() in expected_counts
    recurrence.sync()
    assert recurrence.times.all().count() in expected_counts


@pytest.mark.django_db()
def test_last_day_of_month_recurrence(single_event):  # noqa
    """
    Create and test weekly recurrence
    """
    original_weekday = single_event.times.first().start.weekday()
    anchor_event_time = single_event.times.first()
    recurrence = models.EventRecurrence.objects.create(
        event=single_event,
        event_time_anchor=single_event.times.first(),
        last_week_of_month=True,
    )
    recurrence.sync()

    assert recurrence.times.all().first() == anchor_event_time
    for event_time in recurrence.times.all():
        assert event_time.start.weekday() == original_weekday
        if event_time != anchor_event_time:
            __, last_day = calendar.monthrange(
                event_time.start.year, event_time.start.month
            )
            assert event_time.start.day > last_day - 7

    expected_counts = [default_length_days // 30, default_length_days // 30 + 1]
    assert recurrence.times.all().count() in expected_counts
    recurrence.sync()
    assert recurrence.times.all().count() in expected_counts


@pytest.mark.django_db()
def test_edit_weekly_recurrence(single_event):  # noqa
    """
    Create and test weekly recurrence
    """
    recurrence = models.EventRecurrence.objects.create(
        event=single_event,
        event_time_anchor=single_event.times.first(),
        every_week=True,
    )
    recurrence.sync()
    # Because the first event is now(), we will always fit 53 events in default_length_days days
    expected_count = default_length_days // 7 + 1
    assert recurrence.times.all().count() == expected_count

    new_anchor_start_time = timedelta_fixed_time(
        recurrence.event_time_anchor.start, days=1
    )
    # Push the anchor event 1 day and save
    recurrence.event_time_anchor.start = new_anchor_start_time
    recurrence.event_time_anchor.end = timedelta_fixed_time(
        recurrence.event_time_anchor.end, days=1
    )
    recurrence.event_time_anchor.save()
    recurrence.sync()

    for i, event_time in enumerate(recurrence.times.all()):
        assert event_time.start == timedelta_fixed_time(
            new_anchor_start_time, days=7 * i
        )


@pytest.mark.django_db()
def test_shorten_weekly_recurrence(single_event):  # noqa
    """
    Create and test weekly recurrence
    """
    recurrence = models.EventRecurrence.objects.create(
        event=single_event,
        event_time_anchor=single_event.times.first(),
        every_week=True,
    )
    recurrence.sync()
    # Because the first event is now(), we will always fit 53 events in default_length_days days
    expected_count = default_length_days // 7 + 1
    assert recurrence.times.all().count() == expected_count

    original_count = recurrence.times.all().count()
    recurrence.end = timedelta_fixed_time(
        recurrence.event_time_anchor.start, days=default_length_days - 7
    ).date()
    recurrence.sync()
    assert recurrence.times.filter(start__gte=recurrence.end).count() == 0
    assert recurrence.times.all().count() == original_count - 1


@pytest.mark.django_db()
def test_recurrence_dst_backwards(single_event):  # noqa
    now = get_now()
    if now.month > 10 or (now.month == 10 and now.day >= 10):
        year = now.year + 1
    else:
        year = now.year

    # Put the beginning of the event just before DST change backwards
    first_time = single_event.times.first()
    first_time.start = first_time.start.replace(day=10, month=10, year=year)
    first_time.end = first_time.end.replace(day=10, month=10, year=year)
    first_time.save()

    recurrence = models.EventRecurrence.objects.create(
        event=single_event,
        event_time_anchor=first_time,
        every_week=True,
    )

    recurrence.sync(create_old_times=True)

    for time in recurrence.times.all():
        assert localtime(time.end).hour == localtime(first_time.end).hour
