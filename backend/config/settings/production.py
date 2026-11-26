from .base import *  # noqa: F403

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

if SECRET_KEY == "unsafe-local-only":  # noqa: F405
    raise RuntimeError("DJANGO_SECRET_KEY is required in production")
