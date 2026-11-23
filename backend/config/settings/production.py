from .base import *  # noqa: F403

if SECRET_KEY == "unsafe-local-only":  # noqa: F405
    raise RuntimeError("DJANGO_SECRET_KEY is required in production")
