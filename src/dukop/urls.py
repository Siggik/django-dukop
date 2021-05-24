"""
dukop URL Configuration.

The ``urlpatterns`` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/

Examples:
    Function views
        1. Add an import: from dukop.apps.my_app import views
        2. Add a URL to urlpatterns: path("", views.home, name="home")
    Class-based views
        1. Add an import: from dukop.apps.other_app.views import Home
        2. Add a URL to urlpatterns: path("", Home.as_view(), name="home")
    Including another URLconf
        1. Import the include() function: from django.urls import include, path
        2. Add a URL to urlpatterns: path("blog/", include("dukop.apps.blog.urls"))

"""
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include
from django.urls import path
from dukop.apps.sync_old.views import RedirectOld

urlpatterns = [path("events/<int:pk>", RedirectOld.as_view())] + i18n_patterns(
    path("admin/", admin.site.urls),
    path("news/", include("dukop.apps.news.urls")),
    path("users/", include("dukop.apps.users.urls")),
    path("", include("dukop.apps.calendar.urls")),
)

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = (
        [path("__debug__/", include(debug_toolbar.urls))]
        + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
        + urlpatterns
    )
