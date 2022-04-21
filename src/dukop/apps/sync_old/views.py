from django.http.response import Http404
from django.urls.base import reverse
from django.utils.translation import activate
from django.utils.translation import get_language
from django.views.generic.base import RedirectView
from dukop.apps.calendar.models import OldEventSync


class RedirectOld(RedirectView):

    permanent = True

    def get_redirect_url(self, pk=0):

        try:
            event_sync = OldEventSync.objects.get(old_fk=pk)
        except OldEventSync.DoesNotExist:
            raise Http404()
        except OldEventSync.MultipleObjectsReturned:
            event_sync = OldEventSync.objects.filter(old_fk=pk).last()

        cur_language = get_language()

        try:
            locale = self.request.GET.get("locale") or "en"
            locale = locale[:2]
            activate(locale)
            url = reverse("calendar:event_detail", kwargs={"pk": event_sync.event.id})
        finally:
            activate(cur_language)

        return url
