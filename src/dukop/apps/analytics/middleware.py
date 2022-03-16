import hashlib

from django.conf import settings

from . import models


def analytics_middleware(get_response):
    def middleware(request):
        response = get_response(request)

        # Currently, ignore DNT headers as we are not tracking stuff in these
        # analytics, we just record an anonymous visit no more explicit than
        # a session ID that's generated. We hash the session ID in a hopefully
        # irreversible way.
        if True or not request.META.get("HTTP_DNT", "0") == "1":

            if not request.session or not request.session.session_key:
                request.session.save()

            # Stuff that we could analyze
            # page = {
            #     'agent': request.META.get('HTTP_USER_AGENT', ''),
            #     'path': request.path,
            #     'referrer': request.META.get('HTTP_REFERRER', ''),
            #     'session_key': request.session._get_or_create_session_key(),
            #     'is_authenticated': request.user.is_authenticated
            # }

            ignore = False
            if hasattr(settings, "ANALYTICS_IGNORE_PATHS"):
                if any(
                    request.path.startswith(path)
                    for path in settings.ANALYTICS_IGNORE_PATHS
                ):
                    ignore = True

            visitor_hash = hashlib.sha256(
                str(
                    request.session._get_or_create_session_key()
                    + settings.SECRET_KEY
                    + getattr(
                        settings, "DUKOP_ANALYTICS_SALT", "should_have_been_random"
                    )
                ).encode("utf-8")
            ).hexdigest()

            path_split = request.path.split("/")

            if path_split[1] in (lang[0] for lang in settings.LANGUAGES):
                language_code = path_split[1]
            else:
                language_code = None

            # If we should not ignore this path and a language code is present
            if not ignore and language_code and request.sphere:
                request.dukop_visit, _ = models.Visit.objects.get_or_create(
                    visitor_hash=visitor_hash,
                    language_code=path_split[1],
                    sphere=request.sphere,
                )

        else:
            pass  # DNT

        return response

    return middleware
