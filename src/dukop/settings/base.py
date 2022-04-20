"""
Django settings for dukop project.

# https://docs.djangoproject.com/en/2.1/ref/settings/
"""
import pathlib

from django.urls.base import reverse_lazy
from django.utils.translation import gettext_lazy as _

# Build paths inside the project like this: str(BASE_DIR / "static")
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent

DEBUG = False

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "compressor",
    "dukop.apps.analytics",
    "dukop.apps.calendar",
    "dukop.apps.news",
    "dukop.apps.users",
    "dukop.apps.utils",
    "sekizai",
    "sorl.thumbnail",
    "markdownfield",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",  # Security first
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",  # Set some sensible defaults, now, before responses are modified
    "django.contrib.auth.middleware.AuthenticationMiddleware",  # Uses sessions
    "django.contrib.messages.middleware.MessageMiddleware",  # Uses sessions
    "django.middleware.clickjacking.XFrameOptionsMiddleware",  # Protects against clickjacking
    "django.middleware.locale.LocaleMiddleware",
    "csp.middleware.CSPMiddleware",  # Modifies/sets CSP headers
    "dukop.apps.calendar.middleware.sphere_middleware",
    "dukop.apps.analytics.middleware.analytics_middleware",
    "django.contrib.sites.middleware.CurrentSiteMiddleware",
]

ROOT_URLCONF = "dukop.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(BASE_DIR / "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.request",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "sekizai.context_processors.sekizai",
                "dukop.apps.calendar.context_processors.dukop_sphere",
            ]
        },
    }
]

WSGI_APPLICATION = "dukop.wsgi.application"

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 9,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


AUTH_USER_MODEL = "users.User"

LOGIN_URL = "users:login"
# AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']

# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGES = [("en", _("English")), ("da", _("Danish"))]
LANGUAGE_CODE = "da"

LOCALE_PATHS = [str(BASE_DIR / "locale")]

TIME_ZONE = "Europe/Copenhagen"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = "/static/"

STATIC_ROOT = str(BASE_DIR.parent.parent / "staticfiles")

STATICFILES_DIRS = [str(BASE_DIR / "static")]

STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
)

# Media files (uploaded by a user)
# https://docs.djangoproject.com/en/2.1/topics/files/

MEDIA_URL = "/media/"

MEDIA_ROOT = str(BASE_DIR.parent.parent / "media")

SITE_ID = 1

# SESSION AGE 24 hours
# This makes analytics fairly accurate, but it can be expanded if it's too
# annoying
SESSION_COOKIE_AGE = 60 * 60 * 24

# This is an annoying setting for django-markdownfield
# Would be ideal if it could be replaced with something using django.contrib.sites
# Avoid using it elsewhere.
SITE_URL = "https://beta.dukop.dk"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "formatters": {
        "django.server": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[%(server_time)s] %(message)s",
        }
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
        },
        "console_debug_false": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "logging.StreamHandler",
        },
        "django.server": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "django.server",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "console_debug_false", "mail_admins"],
            "level": "INFO",
        },
        "django.server": {
            "handlers": ["django.server"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

COMPRESS_PRECOMPILERS = (("text/x-scss", "django_libsass.SassCompiler"),)
COMPRESS_FILTERS = {
    # CssAbsoluteFilter is incredibly slow, especially when dealing with our _flags.scss
    # However, we don't need it if we consequently use the static() function in Sass
    # 'compressor.filters.css_default.CssAbsoluteFilter',
    "css": ["compressor.filters.cssmin.CSSCompressorFilter"],
}

LOGIN_REDIRECT_URL = "/"
LOGIN_URL = reverse_lazy("users:login")
LOGOUT_URL = reverse_lazy("users:logout")

# Necessary because of unsupported RGBA
# See: https://github.com/jazzband/sorl-thumbnail/issues/564
THUMBNAIL_PRESERVE_FORMAT = True

CSP_STYLE_SRC = ["'self'", "'unsafe-inline'"]
CSP_IMG_SRC = ["'self'", "data:"]

# This sucks
# https://code.djangoproject.com/ticket/15727
CSP_EXCLUDE_URL_PREFIXES = ("/en/admin",)

# We can have quite long forms when people submit event recurrences
DATA_UPLOAD_MAX_NUMBER_FIELDS = 2000  # higher than the count of fields

# Allows a redirect straight to the "secret" URL where the one-time token can be entered
DUKOP_TOKEN_ALLOW_REDIRECT = True
