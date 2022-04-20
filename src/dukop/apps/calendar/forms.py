from django import forms
from django.forms.models import inlineformset_factory
from django.utils import timezone
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from dukop.apps.calendar import widgets
from dukop.apps.calendar.utils import get_now
from dukop.apps.calendar.widgets import ImageInput
from dukop.apps.users.models import Group
from dukop.apps.users.models import Location

from . import models


class EventForm(forms.ModelForm):

    (LOCATION_EXISTING, LOCATION_NEW, LOCATION_TBA, LOCATION_ONLINE_ONLY) = range(4)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        initial = kwargs.get("initial", {})
        instance = kwargs.get("instance", None)
        if instance and instance.pk:
            if instance.location:
                initial["location_choice"] = self.LOCATION_EXISTING
            elif instance.location_tba:
                initial["location_choice"] = self.LOCATION_TBA
            elif instance.venue_name:
                initial["location_choice"] = self.LOCATION_NEW
            elif instance.online:
                initial["location_choice"] = self.LOCATION_ONLINE_ONLY
            else:
                initial["location_choice"] = self.LOCATION_EXISTING

            if instance.recurrences.exists():
                initial["recurrence_choice"] = True

        if instance and instance.pk:
            initial["spheres"] = instance.spheres.all().values_list("id", flat=True)

        kwargs["initial"] = initial
        super().__init__(*args, **kwargs)

    spheres = forms.ModelMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        queryset=models.Sphere.objects.filter(sub_spheres=None),
        label=_("Calendars"),
        help_text=_(
            "Select which versions of calendar spheres this event is relevant for."
        ),
        required=True,
    )

    location = forms.ModelChoiceField(
        queryset=Location.objects.filter(
            deactivated=False, is_restricted=False
        ).distinct(),
        required=False,
        label=_("Location"),
        help_text=_(
            "Choose an existing location and add this event to the location's list of events"
        ),
    )

    location_choice = forms.TypedChoiceField(
        choices=[
            (LOCATION_EXISTING, "existing"),
            (LOCATION_NEW, "new"),
            (LOCATION_TBA, "tba"),
            (LOCATION_ONLINE_ONLY, "online"),
        ],
        coerce=lambda val: int(val),
        widget=forms.RadioSelect(),
        required=True,
    )

    location_new = forms.BooleanField(
        label=_("Save location"),
        help_text=_("Make the location available for other events later"),
        required=False,
    )

    recurrence_choice = forms.BooleanField(
        widget=forms.RadioSelect(),
        required=False,
        initial=False,
    )

    class Meta:
        model = models.Event
        fields = (
            "name",
            "description",
            "is_cancelled",
            "online",
            "location",
            "venue_name",
            "street",
            "zip_code",
            "city",
            "spheres",
            "location_choice",
        )

    def save(self, commit=True):
        """
        The implementation of commit is a bit false: We know that this can be
        called with commit=False from inheriting classes, but we will still
        create new locations. To change this behavior, wrap calls in
        transaction.atomic
        """

        instance = super().save(commit=False)
        location_choice = self.cleaned_data["location_choice"]

        # This should be overwritten explicitly
        instance.location_tba = False

        if location_choice == self.LOCATION_EXISTING and instance.location:
            instance.venue_name = instance.location.name
            instance.street = instance.location.street
            instance.zip_code = instance.location.zip_code
            instance.city = instance.location.city

        elif location_choice == self.LOCATION_NEW:
            if self.cleaned_data["location_new"]:
                location = Location.objects.create(
                    name=instance.venue_name,
                    street=instance.street,
                    zip_code=instance.zip_code,
                    city=instance.city,
                )
                location.members.add(self.user)
                instance.location = location

        elif location_choice == self.LOCATION_TBA:
            instance.location = None
            instance.venue_name = None
            instance.street = None
            instance.zip_code = None
            instance.city = None
            instance.location_tba = True

        elif location_choice == self.LOCATION_ONLINE_ONLY:
            instance.location = None
            instance.venue_name = None
            instance.street = None
            instance.zip_code = None
            instance.city = None
            instance.online = True

        if commit:
            instance.save()
        return instance


class CreateEventForm(EventForm):

    HOST_EXISTING, HOST_NEW, HOST_NONE = range(3)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.user:
            if self.user.is_superuser:
                self.fields["host"].queryset = Group.objects.filter(
                    deactivated=False, location=None
                )
            else:
                self.fields["host"].queryset = Group.objects.filter(
                    members=self.user, deactivated=False
                )

    host_choice = forms.TypedChoiceField(
        choices=[
            (HOST_EXISTING, "existing"),
            (HOST_NEW, "new"),
            (HOST_NONE, "unspecified"),
        ],
        coerce=lambda val: int(val),
        widget=forms.RadioSelect(),
        required=False,
    )

    host = forms.ModelChoiceField(
        queryset=Group.objects.none(),
        required=False,
        label=_("Host group"),
        help_text=_("Choose one of your existing groups or create a new one"),
    )

    new_host = forms.CharField(
        label=_("New group"),
        help_text=_(
            "Name of the new group, for instance 'Marxist Book Reading Circle'"
        ),
        required=False,
    )

    class Meta(EventForm.Meta):
        fields = (
            "name",
            "description",
            "online",
            "host",
            "new_host",
            "location",
            "venue_name",
            "street",
            "zip_code",
            "city",
            "spheres",
            "location_choice",
            "host_choice",
        )
        help_texts = {
            "host": _(
                "A group may host an event and be displayed as the author of the event text. You can only choose an existing group if you have been allowed membership of that group."
            )
        }

    def save(self, commit=True):

        instance = super().save(commit=False)

        # We have default published=False for new instances
        instance.published = False

        host_choice = self.cleaned_data["host_choice"]

        if host_choice == self.HOST_NEW:
            host = Group.objects.create(name=self.cleaned_data["new_host"])
            host.members.add(self.user)
            self.host = host
        elif host_choice == self.HOST_NONE:
            self.host = None

        if commit:
            instance.save()

        return instance


class EventCancelForm(forms.ModelForm):
    class Meta:
        model = models.Event
        fields = ("is_cancelled",)


class EventPublishForm(forms.ModelForm):
    class Meta:
        model = models.Event
        fields = ("published",)


class EventDeleteForm(forms.ModelForm):
    def save(self, commit=True):
        event = super().save(commit=False)
        event.deleted_on = timezone.now()
        event.save()
        return event

    class Meta:
        model = models.Event
        fields = ("deleted",)
        help_texts = {"deleted": _("Confirm to permanently remove this event")}


class EventTimeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        initial = kwargs.get("initial", {})
        # default_start = (timezone.now() + timedelta(days=1)).replace(
        #     hour=12, minute=0, second=0
        # )
        # initial.setdefault("start", default_start)
        kwargs["initial"] = initial
        super().__init__(*args, **kwargs)

    start = forms.SplitDateTimeField(widget=widgets.SplitDateTimeWidget())
    end = forms.SplitDateTimeField(widget=widgets.SplitDateTimeWidget(), required=False)

    def clean_start(self):
        start = self.cleaned_data.get("start")
        if self.has_changed() and start < get_now():
            raise forms.ValidationError(gettext("Start cannot be in the past."))
        return start

    def clean_end(self):
        start = self.cleaned_data.get("start")
        end = self.cleaned_data.get("end")
        if self.has_changed() and start and end and start >= end:
            raise forms.ValidationError(gettext("End time has to be after start time."))
        return end

    class Meta:
        model = models.EventTime
        fields = ["start", "end"]


class EventTimeUpdateForm(EventTimeForm):
    class Meta(EventTimeForm.Meta):
        fields = EventTimeForm.Meta.fields + ["is_cancelled"]


class EventUpdateImageForm(forms.ModelForm):
    cover_image = forms.BooleanField(
        widget=forms.CheckboxInput(), required=False, initial=True
    )
    extra_images = forms.BooleanField(
        widget=forms.CheckboxInput(), required=False, initial=False
    )

    class Meta:
        model = models.Event
        fields = ()


class EventImageForm(forms.ModelForm):

    image = forms.ImageField(
        widget=ImageInput,
        label=_("Image file"),
        help_text=_(
            "Allowed formats: JPEG, PNG, GIF. Please upload high resolution (>1000 pixels wide). "
        ),
    )

    class Meta:
        model = models.EventImage
        fields = ("image",)


class EventLinkForm(forms.ModelForm):
    class Meta:
        model = models.EventLink
        fields = ("link",)


class EventRecurrenceForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields["interval_type"].initial = self.instance.recurrence_type

    interval_type = forms.ChoiceField(
        choices=[("", "----")] + models.EventRecurrence.RECURRENCE_TYPES,
        required=True,
    )

    end = forms.DateField(required=False, widget=widgets.DateWidget())

    def save(self, commit=True):
        recurrence = super().save(commit=commit)
        for field_name, __ in models.EventRecurrence.RECURRENCE_TYPES:
            setattr(recurrence, field_name, False)
        setattr(recurrence, self.cleaned_data["interval_type"], True)
        return recurrence

    class Meta:
        model = models.EventRecurrence
        fields = ("end",)


class EventRecurrenceTimesForm(forms.ModelForm):

    start = forms.SplitDateTimeField(widget=widgets.SplitDateTimeWidget())
    end = forms.SplitDateTimeField(widget=widgets.SplitDateTimeWidget(), required=False)
    description = forms.CharField(
        required=False,
        label=_("Unique description"),
        widget=forms.Textarea(
            attrs={
                "placeholder": _(
                    "Enter a unique description to be displayed in place of the general event description..."
                ),
                "class": "event-recurrence-times-description",
            },
        ),
    )

    def clean_end(self):
        start = self.cleaned_data.get("start")
        end = self.cleaned_data.get("end")
        if start and end and start >= end:
            raise forms.ValidationError(gettext("End time has to be after start time."))
        return end

    class Meta:
        model = models.EventTime
        fields = ["start", "end", "description", "is_cancelled"]


class OpeningHoursForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance:
            self.fields["interval_type"].initial = (
                self.instance.recurrence_type
                or models.Recurrence.RECURRENCE_TYPES[0][0]
            )

    interval_type = forms.ChoiceField(
        choices=[("", "----")] + models.Recurrence.RECURRENCE_TYPES,
        required=True,
        initial=models.Recurrence.RECURRENCE_TYPES[0][0],
    )

    def save(self, commit=True):
        recurrence = super().save(commit=commit)
        for field_name, __ in models.Recurrence.RECURRENCE_TYPES:
            setattr(recurrence, field_name, False)
        setattr(recurrence, self.cleaned_data["interval_type"], True)
        recurrence.save()
        return recurrence

    class Meta:
        model = models.OpeningHours
        fields = ["weekday", "opens", "closes"]
        widgets = {
            "opens": forms.TimeInput(attrs={"type": "time"}),
            "closes": forms.TimeInput(attrs={"type": "time"}),
        }


EventTimeFormSet = inlineformset_factory(
    models.Event,
    models.EventTime,
    EventTimeForm,
    extra=5,
    max_num=5,
    min_num=1,
    validate_min=True,
)

EventTimeUpdateFormSet = inlineformset_factory(
    models.Event,
    models.EventTime,
    EventTimeUpdateForm,
    extra=5,
    max_num=5,
    min_num=1,
    validate_min=True,
)

EventImageFormSet = inlineformset_factory(
    models.Event, models.EventImage, EventImageForm, extra=5, max_num=5
)
EventLinkFormSet = inlineformset_factory(
    models.Event, models.EventLink, EventLinkForm, extra=5, max_num=5
)
EventRecurrenceFormSet = inlineformset_factory(
    models.Event, models.EventRecurrence, EventRecurrenceForm, extra=2, max_num=2
)
EventRecurrenceTimesFormSet = inlineformset_factory(
    models.Event,
    models.EventTime,
    EventRecurrenceTimesForm,
    extra=0,
    can_delete=False,
)

OpeningHoursFormSet = inlineformset_factory(
    Location,
    models.OpeningHours,
    OpeningHoursForm,
    extra=7,
    can_delete=True,
)
