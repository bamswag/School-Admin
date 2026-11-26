from django.urls import path

from .views import login_view, logout_view, session_view

urlpatterns = [
    path("session/", session_view, name="auth-session"),
    path("login/", login_view, name="auth-login"),
    path("logout/", logout_view, name="auth-logout"),
]
