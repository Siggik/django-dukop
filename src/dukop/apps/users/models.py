import random
import uuid
from datetime import timedelta

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """The user manager class."""

    def token_eligible(self):
        return (
            self.filter(token_expiry__gte=timezone.now())
            .exclude(token_uuid=None)
            .exclude(token_passphrase=None)
            .exclude(token_passphrase="")
        )

    def create_user(self, password: str = None, **kwargs):
        user = self.model(**kwargs)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def create_superuser(self, password: str, **kwargs):
        user = self.create_user(password=password, **kwargs)
        user.is_staff = True
        user.is_superuser = True
        user.save(update_fields=["is_staff", "is_superuser"])
        return user


class User(PermissionsMixin, AbstractBaseUser):

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "email"

    objects = UserManager()

    nick = models.CharField(
        max_length=60,
        null=True,
        blank=True,
        verbose_name=_("Nickname"),
        help_text=_(
            "This name is displayed at events that you host or to other members of groups that you are in."
        ),
    )
    email = models.EmailField(
        unique=True,
        verbose_name=_("email"),
        help_text=_(
            "Your email address will be used for password resets and notification about your event/submissions."
        ),
    )

    is_active = models.BooleanField(default=True)

    # For the Django admin...
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    # Used for confirmations and password reminders to NOT disclose email in URL
    token_uuid = models.UUIDField(default=uuid.uuid4, editable=False, null=True)
    token_expiry = models.DateTimeField(null=True, editable=False)
    token_passphrase = models.CharField(
        null=True,
        blank=True,
        help_text=_("One time passphrase"),
        max_length=128,
    )

    def __str__(self) -> str:
        """Use a useful string representation."""
        return self.get_display_name()

    def get_display_name(self) -> str:
        return self.nick if self.nick else str(_("Unnamed user"))

    def set_token(self):
        """
        A caution: A user can be inactive or banned, do not expect that calling
        this function should change state/permissions of a user.
        """
        self.token_uuid = uuid.uuid4()
        self.token_expiry = timezone.now() + timedelta(minutes=60)
        self.token_passphrase = str(random.randint(0, 100000000)).zfill(8)
        self.save()

    def use_token(self):
        """
        When logging in, mark a token as used
        """
        self.token_uuid = None
        self.token_passphrase = None
        self.save()

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")


class Group(models.Model):

    name = models.CharField(
        max_length=255,
        verbose_name=_("name"),
    )
    members = models.ManyToManyField(User, related_name="dukop_groups", blank=True)

    is_restricted = models.BooleanField(
        default=False,
        help_text=_("Do not allow others to add events to this group"),
    )

    deactivated = models.BooleanField(
        default=False,
        help_text=_("Do not show this group"),
    )

    description = models.TextField(
        blank=True,
        verbose_name=_("description"),
        help_text=_("Enter details, which will be displayed on the group's own page."),
    )

    owner_email = models.EmailField(blank=True, null=True)

    street = models.CharField(
        max_length=255,
        verbose_name=_("street"),
        blank=True,
        null=True,
    )
    city = models.CharField(
        max_length=255,
        verbose_name=_("city"),
        blank=True,
        null=True,
    )
    zip_code = models.CharField(
        verbose_name=_("zip code"),
        blank=True,
        null=True,
        max_length=16,
    )

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Group")
        ordering = ("name",)

    def __str__(self) -> str:
        """Use a useful string representation."""
        return self.name


class Location(Group):
    """
    A location is a group that also has a physical location. Other groups may
    create events here.

    We don't know yet if the location will have direct moderation rights to
    events hosted in its space.
    """

    class Meta:
        verbose_name = _("Location")
        ordering = ("name",)


class GroupLink(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="links")
    link = models.URLField(blank=True, null=True, max_length=2048)
    priority = models.PositiveSmallIntegerField(
        default=0, help_text=_("0=first, 1=second etc.")
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("priority",)
