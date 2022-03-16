from datetime import timedelta

import pytest
from dukop.apps.calendar import models
from dukop.apps.calendar import utils


@pytest.fixture
def default_sphere(db):
    models.Sphere._cached_default = None
    return models.Sphere.get_default()


@pytest.fixture
def single_event(db, default_sphere):
    start = utils.get_now() + timedelta(days=14)
    end = start + timedelta(hours=2)
    event = models.Event.objects.create(
        name="Test event",
        short_description="A short description",
        description="A longer description",
        venue_name="The Place",
    )
    event.spheres.add(default_sphere)
    models.EventTime.objects.create(
        event=event,
        start=start,
        end=end,
    )
    return event


@pytest.fixture
def single_event_3_weeks_past(db, default_sphere):
    models.Sphere._cached_default = None
    start = utils.get_now() - timedelta(days=21)
    start = start.replace(hour=18, minute=0)
    end = start + timedelta(hours=2)
    event = models.Event.objects.create(
        name="Test event",
        short_description="A short description",
        description="A longer description",
        venue_name="The Place",
    )
    event.spheres.add(default_sphere)
    models.EventTime.objects.create(
        event=event,
        start=start,
        end=end,
    )
    return event
