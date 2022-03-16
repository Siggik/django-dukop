from django.db import models


class Visit(models.Model):
    """
    A visit just records that someone was here, we don't analyze where they were
    from or there browser etc. Just stuff that we can very quickly analyze.
    """

    visitor_hash = models.CharField(max_length=32)
    created = models.DateTimeField(auto_now_add=True)
    last_visit = models.DateTimeField(auto_now=True)
    language_code = models.CharField(max_length=6)
    sphere = models.ForeignKey("calendar.Sphere", on_delete=models.PROTECT)


class EventVisit(models.Model):
    """
    A unique record of an event visit. We aren't so interested in more than
    the fact that the event was visited.
    """

    event = models.ForeignKey("calendar.Event", on_delete=models.CASCADE)
    visit = models.ForeignKey("Visit", on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)


# TODO: Create a digest to replace all the garbage analytics created in EventVisit
