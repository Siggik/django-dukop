import pytest
from django.core.management import call_command

from .fixtures_calendar import default_sphere  # noqa


@pytest.mark.django_db()
def test_landing_page(client):
    response = client.get("/en/")
    assert response.status_code == 200
    response = client.get("/", follow=True)
    assert response.status_code == 200


@pytest.mark.django_db()
def test_about_page(client):
    response = client.get("/en/news/about/")
    assert response.status_code == 200


@pytest.mark.django_db()
def test_fixtures(client):
    """
    Test event creation by calling our fixture management command
    """
    call_command("calendar_fixtures", local_image=True)
