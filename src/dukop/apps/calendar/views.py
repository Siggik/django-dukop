from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.db.models import Max
from django.db.models import Min
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.urls.base import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView
from django.views.generic.edit import UpdateView
from django.views.generic.list import ListView
from dukop.apps.calendar.utils import get_now
from dukop.apps.users.models import Group
from dukop.apps.users.models import Location
from ratelimit.decorators import ratelimit

from . import forms
from . import models


class IndexView(TemplateView):

    template_name = "calendar/index.html"

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        c["event_recurrences"] = (
            models.EventRecurrence.objects.filter(
                event__published=True,
                times__start__gte=get_now(),
                times__start__lte=get_now() + timedelta(days=30),
                end__gte=get_now(),
            )
            .values(
                "event__name",
                "event__pk",
                "event__venue_name",
                "pk",
                "every_week",
                "biweekly_even",
                "biweekly_odd",
                "first_week_of_month",
                "second_week_of_month",
                "third_week_of_month",
                "last_week_of_month",
                next=Min("times__start"),
            )
            .order_by("-next")
            .distinct()
        )

        c["locations"] = (
            Location.objects.filter(
                deactivated=False,
                events_here__times__start__gte=get_now() - timedelta(days=1),
                events_here__published=True,
            )
            .values(
                "name",
                "pk",
                latest=Max("events_here__modified"),
                event_count=Count("events_here"),
            )
            .order_by("-latest")
            .distinct()[:30]
        )
        return c


class FeedInstructionView(TemplateView):
    template_name = "calendar/feeds/instructions.html"

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        c["spheres"] = models.Sphere.get_all_cached()
        return c


class EventDetailView(DetailView):

    template_name = "calendar/event/detail.html"
    model = models.Event
    context_object_name = "event"

    def get_queryset(self):
        qs = super().get_queryset()

        if not self.request.user or not self.request.user.is_staff:
            if self.request.user.is_authenticated:
                qs = qs.filter(
                    Q(published=True)
                    | Q(owner_user=self.request.user)
                    | Q(owner_group__members=self.request.user)
                )
            else:
                qs = qs.filter(published=True)
        return qs

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        if self.kwargs.get("time_pk", None):
            c["selected_time"] = models.EventTime.objects.get(pk=self.kwargs["time_pk"])
        return c


class EventProcessFormMixin:
    def get(self, request, *args, **kwargs):
        """Handle GET requests: instantiate a blank version of the form."""
        self.times_form = self.get_times_form_class()(
            instance=self.object,
            queryset=models.EventTime.objects.filter(
                Q(recurrence=None) | Q(recurrence_anchors__id__gt=0)
            ),
        )
        self.links_form = forms.EventLinkFormSet(instance=self.object)
        self.recurrences_form = forms.EventRecurrenceFormSet(instance=self.object)
        self.recurrences_times_form = forms.EventRecurrenceTimesFormSet(
            instance=self.object,
            queryset=models.EventTime.objects.exclude(recurrence=None)
            .future()
            .filter(recurrence_anchors=None),
            prefix="recurrence_times",
        )
        return self.render_to_response(self.get_context_data())

    def _create_formset_instances(self, request):
        self.times_form = self.get_times_form_class()(
            data=request.POST, instance=self.object
        )
        self.links_form = forms.EventLinkFormSet(
            data=request.POST, instance=self.object
        )
        self.recurrences_form = forms.EventRecurrenceFormSet(
            data=request.POST, instance=self.object
        )
        self.recurrences_times_form = forms.EventRecurrenceTimesFormSet(
            data=request.POST,
            instance=self.object,
            prefix="recurrence_times",
            queryset=models.EventTime.objects.exclude(recurrence=None)
            .future()
            .filter(recurrence_anchors=None),
        )

    @method_decorator(ratelimit(key="ip", rate="10/d", method="POST"))
    @method_decorator(ratelimit(key="ip", rate="5/h", method="POST"))
    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: instantiate a form instance with the passed
        POST variables and then check if it's valid.
        """
        form = self.get_form()
        self._create_formset_instances(request)
        if (
            form.is_valid()
            and self.times_form.is_valid()
            and self.links_form.is_valid()
            and self.recurrences_form.is_valid()
            and (
                (not self.object)
                or len(self.recurrences_times_form) == 0
                or self.recurrences_times_form.is_valid()
            )  # Something wrong here? It has been disabled
        ):
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    @transaction.atomic()
    def form_valid(self, form):  # noqa: max-complexity=13
        self.object = form.save()
        event = self.object
        if not event.short_description:
            event.short_description = event.get_short_description()
        if not event.owner_user:
            event.owner_user = self.request.user
        event.save()

        # We need to call this again to re-instantiate the formsets once more
        # with the generated event object.
        self._create_formset_instances(self.request)

        for time_form in self.times_form:
            if time_form.has_changed() and time_form.is_valid():
                time_form.save()

        for link_form in self.links_form:
            if link_form.has_changed() and link_form.is_valid():
                link_form.save()
                for obj in getattr(link_form, "deleted_objects", []):
                    obj.delete()

        if form.cleaned_data["recurrence_choice"]:
            for recurrence_form in self.recurrences_form:
                if recurrence_form.has_changed() and recurrence_form.is_valid():
                    recurrence = recurrence_form.save(commit=False)
                    recurrence.event = event
                    recurrence.event_time_anchor = event.times.all().first()
                    recurrence.save()
                    recurrence.sync()
                    for obj in getattr(recurrence_form, "deleted_objects", []):
                        obj.delete()
        else:
            if self.object.pk:
                for recurrence in self.object.recurrences.all():
                    recurrence.event_time_anchor.recurrence = None
                    recurrence.event_time_anchor.save()
                self.object.recurrences.all().delete()

        for recurrence_time_form in self.recurrences_times_form:
            if recurrence_time_form.has_changed() and recurrence_time_form.is_valid():
                times = recurrence_time_form.save(commit=False)
                times.recurrence_auto = False
                times.save()

        return self.get_success_url()

    def form_invalid(self, form):
        self.forms_had_errors = True
        return super().form_invalid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        c["times"] = self.times_form
        c["links"] = self.links_form
        c["recurrences"] = self.recurrences_form
        c["recurrences_times"] = self.recurrences_times_form
        c["forms_had_errors"] = getattr(self, "forms_had_errors", False)
        return c

    def get_initial(self):
        initial = super().initial
        initial["spheres"] = models.Sphere.objects.filter(id=self.request.sphere.id)
        return initial

    def get_times_form_class(self):
        return forms.EventTimeFormSet


class EventCreateView(EventProcessFormMixin, CreateView):

    template_name = "calendar/event/create.html"
    model = models.Event
    form_class = forms.CreateEventForm

    def get_success_url(self):
        messages.success(
            self.request,
            _("Event '{event_name}' was created").format(event_name=self.object.name),
        )
        return redirect("calendar:event_images_update", pk=self.object.pk)

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        self.object = None
        return super().dispatch(*args, **kwargs)


class EventUpdateView(EventProcessFormMixin, UpdateView):

    template_name = "calendar/event/update.html"
    model = models.Event
    form_class = forms.EventForm

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(*args, **kwargs)

    def get_success_url(self):
        messages.success(
            self.request,
            _("Event '{event_name}' was updated").format(event_name=self.object.name),
        )
        return redirect("calendar:event_dashboard")

    def get_queryset(self):
        qs = DetailView.get_queryset(self)
        if not self.request.user.is_superuser:
            qs = qs.filter(
                Q(owner_user=self.request.user)
                | Q(owner_group__members=self.request.user)
            ).distinct()
        return qs

    def get_times_form_class(self):
        return forms.EventTimeUpdateFormSet


class EventImagesUpdateView(UpdateView):
    form_class = forms.EventUpdateImageForm
    template_name = "calendar/event/update_images.html"
    model = models.Event

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            qs = qs.filter(
                Q(owner_user=self.request.user)
                | Q(owner_group__members=self.request.user)
            ).distinct()
        return qs

    def _create_formset_instances(self, request):
        self.images_form = forms.EventImageFormSet(
            data=request.POST, instance=self.object
        )

    def get(self, request, *args, **kwargs):
        """Handle GET requests: instantiate a blank version of the form."""
        self.images_form = forms.EventImageFormSet(
            prefix="images", instance=self.object
        )
        return self.render_to_response(self.get_context_data())

    @method_decorator(ratelimit(key="ip", rate="10/d", method="POST"))
    @method_decorator(ratelimit(key="ip", rate="5/h", method="POST"))
    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: instantiate a form instance with the passed
        POST variables and then check if it's valid.
        """
        form = self.get_form()
        self._create_formset_instances(request)
        if form.is_valid() and self.images_form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        for cnt, image_form in enumerate(self.images_form):
            if (
                image_form.has_changed()
                and image_form.is_valid()
                and image_form.cleaned_data.get("image")
            ):
                image = image_form.save(commit=False)
                image.priority = cnt
                image.save()
                for obj in getattr(image_form, "deleted_objects", []):
                    obj.delete()

        return self.get_success_url()

    def get_success_url(self):
        if self.object.published:
            messages.success(
                self.request,
                _("You have created '{event_name}', please have a look below.").format(
                    event_name=self.object.name
                ),
            )
            return redirect("calendar:event_detail", pk=self.object.pk)
        else:
            messages.success(
                self.request,
                _("Images for '{event_name}' were updated").format(
                    event_name=self.object.name
                ),
            )
            return redirect("calendar:event_dashboard")

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        c["images"] = self.images_form
        c["forms_had_errors"] = getattr(self, "forms_had_errors", False)
        return c


class EventCancelView(UpdateView):

    template_name = "calendar/event/cancel.html"
    model = models.Event
    form_class = forms.EventCancelForm

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        form.save()
        if form.cleaned_data["is_cancelled"]:
            messages.success(
                self.request,
                _("Event '{event_name}' was cancelled.").format(
                    event_name=self.object.name
                ),
            )
        else:
            messages.success(
                self.request,
                _("Event '{event_name}' was un-cancelled.").format(
                    event_name=self.object.name
                ),
            )
        return redirect("calendar:event_dashboard")

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            qs = qs.filter(
                Q(owner_user=self.request.user)
                | Q(owner_group__members=self.request.user)
            ).distinct()
        return qs


class EventPublishView(UpdateView):

    template_name = "calendar/event/publish.html"
    model = models.Event
    form_class = forms.EventPublishForm

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        form.save()
        if form.cleaned_data["published"]:
            messages.success(
                self.request,
                _("Event '{event_name}' was published.").format(
                    event_name=self.object.name
                ),
            )
        else:
            messages.success(
                self.request,
                _("Event '{event_name}' was unpublished.").format(
                    event_name=self.object.name
                ),
            )
        return redirect("calendar:event_dashboard")

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_superuser:
            qs = qs.filter(
                Q(owner_user=self.request.user)
                | Q(owner_group__members=self.request.user)
            ).distinct()
        return qs


class EventListView(ListView):
    """
    This lists all Event objects -- BUT! Notice that the listing is happening
    via the EventTime relation. We are only ever interested in listing events
    from their occurrence in time, past present or future. The essential feature
    of the list is to be chronological.
    """

    template_name = "calendar/event/list.html"
    model = models.EventTime
    context_object_name = "event_times"
    max_days_lookback = 30

    def dispatch(self, request, *args, **kwargs):
        sphere_id = kwargs.get("sphere_id", None)
        self.sphere = None
        if sphere_id:
            self.sphere = get_object_or_404(models.Sphere, pk=sphere_id)

        self.pivot_date = kwargs.get("pivot_date", None)
        if not self.pivot_date:
            self.pivot_date = timezone.now().date()

        self.pivot_date_end = self.pivot_date + timedelta(days=7)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()

        if not self.request.user or not self.request.user.is_staff:
            q_visible_to_all = Q(event__published=True) & Q(
                start__gte=timezone.now() - timedelta(days=self.max_days_lookback)
            )
            if self.request.user.is_authenticated:
                qs = qs.filter(
                    q_visible_to_all
                    | Q(event__owner_user=self.request.user)
                    | Q(event__owner_group__members=self.request.user)
                )
            else:
                qs = qs.filter(q_visible_to_all)

        qs = qs.filter(start__gte=self.pivot_date, start__lte=self.pivot_date_end)

        if self.sphere:
            qs = qs.filter(event__spheres=self.sphere)

        return qs

    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        c["pivot_date"] = self.pivot_date
        c["pivot_date_end"] = self.pivot_date_end
        c["pivot_date_next"] = self.pivot_date_end
        c["pivot_date_previous"] = self.pivot_date - timedelta(days=7)
        c["sphere"] = self.sphere
        return c


class EventDashboard(ListView):
    """
    This lists all Event objects -- BUT! Notice that the listing is happening
    via the EventTime relation. We are only ever interested in listing events
    from their occurrence in time, past present or future. The essential feature
    of the list is to be chronological.
    """

    template_name = "calendar/event/dashboard.html"
    model = models.Event
    context_object_name = "events"

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(
            Q(owner_user=self.request.user) | Q(owner_group__members=self.request.user)
        ).distinct()
        return qs


def set_sphere_session(request, pk):
    get_object_or_404(models.Sphere, pk=pk)
    request.session["dukop_sphere"] = pk

    next_url = request.GET.get("next")
    if not next_url:
        next_url = reverse("calendar:index")
    return redirect(next_url)


class GroupDetailView(DetailView):

    template_name = "calendar/group/detail.html"

    def get_queryset(self):
        return Group.objects.filter(deactivated=False)


class LocationDetailView(DetailView):

    template_name = "calendar/location/detail.html"
    context_object_name = "location"

    def get_queryset(self):
        return Location.objects.filter(deactivated=False)
