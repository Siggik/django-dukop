import random
from datetime import timedelta

import pytest
from django.urls.base import reverse
from django.utils import timezone
from dukop.apps.calendar import forms
from dukop.apps.calendar import models

from .fixtures_calendar import default_sphere  # noqa
from .fixtures_calendar import single_event  # noqa
from .fixtures_users import single_user  # noqa
from .fixtures_users import SINGLE_USER_PASSWORD


def create_form_data(response):
    """
    A utility function that generates the data for an integration test of EventForm
    """
    # data will receive all the forms field names
    # key will be the field name (as "formx-fieldname"), value will be the string representation.
    data = {}

    # global information, some additional fields may go there
    data["csrf_token"] = response.context["csrf_token"]

    # management form information, needed because of the formset
    for form_name in ["times", "recurrences", "links"]:
        management_form = response.context[form_name].management_form
        for i in "TOTAL_FORMS", "INITIAL_FORMS", "MIN_NUM_FORMS", "MAX_NUM_FORMS":
            data["%s-%s" % (management_form.prefix, i)] = management_form[i].value()

        for i in range(response.context[form_name].total_form_count()):
            # get form index 'i'
            current_form = response.context[form_name].forms[i]

            # retrieve all the fields
            for field_name in current_form.fields:
                value = current_form[field_name].value()
                data["%s-%s" % (current_form.prefix, field_name)] = (
                    value if value is not None else ""
                )
    data["spheres"] = models.Sphere.get_default().pk

    return data


@pytest.mark.django_db(transaction=True)
def test_create_event(single_user, default_sphere, client, settings):  # noqa
    """
    Test basic event creation
    """
    settings.IS_CI_TEST = True
    client.login(username=single_user.email, password=SINGLE_USER_PASSWORD)
    response = client.get(reverse("calendar:event_create"))

    assert response.status_code == 200

    data = create_form_data(response)

    first_times_form = response.context["times"].forms[0]
    start_datetime = timezone.now() + timedelta(days=1)
    data["%s-%s_0" % (first_times_form.prefix, "start")] = start_datetime.date()
    data["%s-%s_1" % (first_times_form.prefix, "start")] = start_datetime.strftime(
        "%H:%M"
    )

    event_name = f"Test event {random.randint(10000, 99999)}"

    data["name"] = event_name
    data["host_choice"] = forms.CreateEventForm.HOST_NEW
    data["location_choice"] = forms.EventForm.LOCATION_NEW
    data["spheres"] = models.Sphere.objects.get(slug="cph").id
    data["new_host"] = "Test group {random.randint(10000, 99999)}"

    response = client.post(reverse("calendar:event_create"), data=data)
    print(response.content)
    assert response.status_code == 302

    assert models.Event.objects.all().latest("id").name == event_name


@pytest.mark.django_db(transaction=True)
def test_create_recurring_event(single_user, default_sphere, client, settings):  # noqa
    """
    Creates an event that recurs weekly
    """
    settings.IS_CI_TEST = True
    client.login(username=single_user.email, password=SINGLE_USER_PASSWORD)
    response = client.get(reverse("calendar:event_create"))
    assert response.status_code == 200

    data = create_form_data(response)

    first_times_form = response.context["times"].forms[0]
    start_datetime = timezone.now() + timedelta(days=1)
    data["%s-%s_0" % (first_times_form.prefix, "start")] = start_datetime.date()
    data["%s-%s_1" % (first_times_form.prefix, "start")] = start_datetime.strftime(
        "%H:%M"
    )

    first_recurrences_form = response.context["recurrences"].forms[0]
    end_datetime = timezone.now() + timedelta(days=100)

    data["%s-%s" % (first_recurrences_form.prefix, "end")] = end_datetime.date()
    data[
        "%s-%s" % (first_recurrences_form.prefix, "interval_type")
    ] = models.EventRecurrence.RECURRENCE_TYPES[0][0]

    event_name = f"Test event {random.randint(10000, 99999)}"

    data["name"] = event_name
    data["host_choice"] = forms.CreateEventForm.HOST_NEW
    data["location_choice"] = forms.EventForm.LOCATION_NEW
    data["recurrence_choice"] = True

    data["new_host"] = "Test group {random.randint(10000, 99999)}"

    response = client.post(reverse("calendar:event_create"), data=data)

    try:
        assert response.status_code == 302
    except AssertionError:
        print(response.context["form"].errors)
        print(response.context["recurrences"].errors)
        raise

    assert models.Event.objects.all().latest("id").name == event_name
    assert models.Event.objects.all().latest("id").times.all().count() >= 100 // 7


@pytest.mark.django_db(transaction=True)
def test_update_event(single_user, single_event, client, settings):  # noqa
    """
    Test basic event creation
    """
    settings.IS_CI_TEST = True
    single_event.owner_user = single_user
    single_event.save()
    client.login(username=single_user.email, password=SINGLE_USER_PASSWORD)
    response = client.get(
        reverse("calendar:event_update", kwargs={"pk": single_event.id})
    )
    assert response.status_code == 200

    data = create_form_data(response)

    first_times_form = response.context["times"].forms[0]
    start_datetime = timezone.now() + timedelta(days=1)
    data["%s-%s_0" % (first_times_form.prefix, "start")] = start_datetime.date()
    data["%s-%s_1" % (first_times_form.prefix, "start")] = start_datetime.strftime(
        "%H:%M"
    )

    event_name = f"Updating event {random.randint(10000, 99999)}"

    data["name"] = event_name
    data["location_choice"] = forms.EventForm.LOCATION_NEW

    data["new_host"] = "Test group {random.randint(10000, 99999)}"

    response = client.post(
        reverse("calendar:event_update", kwargs={"pk": single_event.id}), data=data
    )
    assert response.status_code == 302

    assert models.Event.objects.get(id=single_event.id).name == event_name
