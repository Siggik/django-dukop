import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import SuccessURLAllowedHostsMixin
from django.http.response import HttpResponseRedirect
from django.shortcuts import redirect
from django.shortcuts import resolve_url
from django.urls.base import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.http import is_safe_url
from django.utils.translation import gettext as _
from django.views.generic.base import RedirectView
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from django.views.generic.edit import UpdateView
from ratelimit.decorators import ratelimit

from . import email
from . import forms
from . import models


class PasswordResetView(auth_views.PasswordResetView):
    """
    This view is pretty much replaced by the current login view, which
    implements the 1-time password login.
    """

    email_template_name = "users/password_reset_email.html"
    success_url = reverse_lazy("users:password_reset_done")


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    success_url = reverse_lazy("users:password_reset_complete")


class PasswordChangeView(auth_views.PasswordChangeView):
    success_url = reverse_lazy("users:password_change_done")


class LoginView(FormView, SuccessURLAllowedHostsMixin):

    template_name = "users/login.html"
    form_class = forms.EmailLogin
    redirect_field_name = "next"

    @method_decorator(
        ratelimit(
            group="dukop_noauth", key="ip", rate="10/d", method="POST", block=True
        )
    )
    @method_decorator(
        ratelimit(group="dukop_noauth", key="ip", rate="8/h", method="POST", block=True)
    )
    def dispatch(self, request, *args, **kwargs):
        if request.GET.get("next", "") and request.method == "GET":
            messages.info(request, _("Please log in before proceeding"))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        c = FormView.get_context_data(self, **kwargs)
        c["next"] = self.request.GET.get("next", "")
        c["password_form"] = forms.PasswordLogin()
        c["signup_form"] = forms.SignupForm()
        return c

    def form_valid(self, form):
        messages.success(self.request, "Check your inbox")
        user = None
        try:
            user = models.User.objects.get(email=form.cleaned_data["email"])
            passphrase = user.set_token()
            mail = email.UserToken(
                self.request,
                passphrase=passphrase,
                user=user,
                next=self.request.POST.get(self.redirect_field_name, ""),
            )
            # Suppress output, users cannot know whether this went well or not
            mail.send_with_feedback(no_message=True)
        except models.User.DoesNotExist:
            # The email did not exist, but we are not going to do anything differently because of this.
            pass
        self.request.session["email_token"] = form.cleaned_data["email"]

        # Redirect straight to a valid token login page or a dummy one in case
        # we allow for this...
        if getattr(settings, "DUKOP_TOKEN_ALLOW_REDIRECT", False):
            return redirect(
                "users:login_token", token=user.token_uuid if user else uuid.uuid4()
            )
        else:
            return redirect("users:login_token_sent")


class LoginPasswordView(FormView, SuccessURLAllowedHostsMixin):

    template_name = "users/login_password.html"
    form_class = forms.PasswordLogin
    redirect_field_name = "next"

    @method_decorator(
        ratelimit(
            group="dukop_noauth", key="ip", rate="30/d", method="POST", block=True
        )
    )
    @method_decorator(
        ratelimit(group="dukop_noauth", key="ip", rate="8/h", method="POST", block=True)
    )
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        login(self.request, form.user_cache, backend=None)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        url = self.get_redirect_url()
        return url or resolve_url(settings.LOGIN_REDIRECT_URL)

    def get_redirect_url(self):
        """Return the user-originating redirect URL if it's safe."""
        redirect_to = self.request.POST.get(
            self.redirect_field_name, self.request.GET.get(self.redirect_field_name, "")
        )
        url_is_safe = is_safe_url(
            url=redirect_to,
            allowed_hosts=self.get_success_url_allowed_hosts(),
            require_https=self.request.is_secure(),
        )
        return redirect_to if url_is_safe else ""


class LoginTokenSentView(TemplateView):

    template_name = "users/login_token_sent.html"

    def get_context_data(self, **kwargs):
        c = TemplateView.get_context_data(self, **kwargs)
        c["email_token"] = self.request.session["email_token"]
        return c


class LoginTokenView(FormView, SuccessURLAllowedHostsMixin):

    template_name = "users/login_token.html"
    form_class = forms.TokenLogin
    redirect_field_name = "next"

    @method_decorator(
        ratelimit(
            group="dukop_noauth", key="ip", rate="30/d", method="POST", block=True
        )
    )
    @method_decorator(
        ratelimit(group="dukop_noauth", key="ip", rate="8/h", method="POST", block=True)
    )
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = FormView.get_form_kwargs(self)
        kwargs["token_uuid"] = self.kwargs["token"]
        return kwargs

    def get_context_data(self, **kwargs):
        c = FormView.get_context_data(self, **kwargs)
        c["next"] = self.request.POST.get(
            self.redirect_field_name, self.request.GET.get(self.redirect_field_name, "")
        )
        c["DUKOP_TOKEN_ALLOW_REDIRECT"] = getattr(
            settings, "DUKOP_TOKEN_ALLOW_REDIRECT", False
        )
        return c

    def form_valid(self, form):
        # Find a suitable backend.
        form.user.use_token()
        login(self.request, form.user, backend=settings.AUTHENTICATION_BACKENDS[0])
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        url = self.get_redirect_url()
        return url or resolve_url(settings.LOGIN_REDIRECT_URL)

    def get_redirect_url(self):
        """Return the user-originating redirect URL if it's safe."""
        redirect_to = self.request.POST.get(
            self.redirect_field_name, self.request.GET.get(self.redirect_field_name, "")
        )
        url_is_safe = is_safe_url(
            url=redirect_to,
            allowed_hosts=self.get_success_url_allowed_hosts(),
            require_https=self.request.is_secure(),
        )
        return redirect_to if url_is_safe else ""


class SignupView(FormView):

    template_name = "users/signup.html"
    form_class = forms.SignupForm
    redirect_field_name = "next"

    @method_decorator(
        ratelimit(
            group="dukop_noauth", key="ip", rate="10/d", method="POST", block=True
        )
    )
    @method_decorator(
        ratelimit(group="dukop_noauth", key="ip", rate="5/h", method="POST", block=True)
    )
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        c = FormView.get_context_data(self, **kwargs)
        c["next"] = self.request.POST.get(
            self.redirect_field_name, self.request.GET.get(self.redirect_field_name, "")
        )
        return c

    def form_valid(self, form):

        next_url = self.request.POST.get("next", "")
        try:
            user = models.User.objects.get(email=form.cleaned_data["email"])
            passphrase = user.set_token()
            mail = email.UserToken(
                self.request, passphrase=passphrase, user=user, next=next_url
            )
            mail.send_with_feedback(success_msg=_("Check your inbox"))
            messages.success(
                self.request,
                _("If the email isn't there in 2 minutes, check your spam folder."),
            )
        except models.User.DoesNotExist:
            user = models.User.objects.create_user(email=form.cleaned_data["email"])
            user.is_active = True  # The user is active by default
            user.save()
            passphrase = user.set_token()
            mail = email.UserConfirm(
                self.request, passphrase=passphrase, user=user, next=next_url
            )
            # Give the same feedback regardless so this isn't used to lookup
            # email addresses
            mail.send_with_feedback(success_msg=_("Check your inbox"))

        self.request.session["user_confirm_pending_id"] = user.id

        return redirect("users:signup_confirm")


class SignupConfirmView(TemplateView):

    template_name = "users/signup_confirm.html"


class SignupConfirmRedirectView(RedirectView):
    def get_redirect_url(self):
        uuid = self.kwargs["uuid"]
        if self.kwargs["token"] == forms.get_confirm_code(uuid):
            redirect("users:confirmed")  # TODO
        redirect("users:confirm_nope")  # TODO


class UserUpdate(UpdateView):

    template_name = "users/update.html"
    form_class = forms.UpdateForm

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        self.user = models.User.objects.get(id=self.request.user.id)
        return self.user

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.user
        return kwargs

    def form_valid(self, form):
        user = form.save()
        new_password = form.cleaned_data.get("new_password1")
        if new_password:
            user = authenticate(username=user.get_username(), password=new_password)
            login(self.request, user)
        messages.success(
            self.request,
            _("Your profile updates were saved."),
        )
        return redirect("users:update")
