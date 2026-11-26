from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.utils.crypto import salted_hmac
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .serializers import LoginSerializer

LOGIN_FAILURE_LIMIT = 5
LOGIN_FAILURE_WINDOW = 300


def session_payload(user):
    if not user.is_authenticated:
        return {"authenticated": False, "user": None, "memberships": []}

    memberships = user.memberships.filter(active=True, organisation__is_active=True)
    memberships = memberships.select_related("organisation").order_by("organisation__code")
    return {
        "authenticated": True,
        "user": {"id": str(user.pk), "email": user.email},
        "memberships": [
            {
                "role": membership.role,
                "organisation": {
                    "id": str(membership.organisation_id),
                    "code": membership.organisation.code,
                    "name": membership.organisation.name,
                    "type": membership.organisation.organisation_type,
                },
            }
            for membership in memberships
        ],
    }


def failure_key(kind, value):
    digest = salted_hmac(f"demo-login-{kind}", value, algorithm="sha256").hexdigest()
    return f"demo-login:{kind}:{digest}"


def record_failure(key):
    try:
        cache.incr(key)
    except ValueError:
        if not cache.add(key, 1, timeout=LOGIN_FAILURE_WINDOW):
            cache.incr(key)


@never_cache
@ensure_csrf_cookie
@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def session_view(request):
    return Response(session_payload(request.user))


@never_cache
@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
@csrf_protect
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    email = serializer.validated_data["email"].lower()
    keys = (failure_key("email", email), failure_key("ip", request.META.get("REMOTE_ADDR", "")))
    # shortcut: process-local limit, replace with a shared atomic limiter before multi-worker use
    if any(cache.get(key, 0) >= LOGIN_FAILURE_LIMIT for key in keys):
        return Response({"message": "Too many failed login attempts."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

    user = authenticate(request, email=email, password=serializer.validated_data["password"])
    if user is None:
        for key in keys:
            record_failure(key)
        return Response({"message": "Invalid email or password."}, status=status.HTTP_401_UNAUTHORIZED)

    login(request, user)
    return Response(session_payload(user))


@never_cache
@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
@csrf_protect
def logout_view(request):
    logout(request)
    return Response(session_payload(request.user))
