"""
For development purposes: Create a bunch of random events at random times.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from dukop.apps.calendar import models


class Command(BaseCommand):
    help = "Cleans up the calendar"

    @transaction.atomic
    def handle(self, *args, **options):
        threshold_days = 30
        threshold = timezone.now() - timedelta(days=threshold_days)
        to_delete = models.Event.objects.filter(deleted=True, deleted_on__lte=threshold)
        print("Starting calendar cleanup job")
        print("Deleting {} events".format(to_delete.count()))

        to_delete.delete()

        print("Done")
