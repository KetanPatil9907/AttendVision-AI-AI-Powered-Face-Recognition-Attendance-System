from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from accounts import views

urlpatterns = [
    path("login", views.LoginView.as_view(), name="auth-login"),
    path("refresh", TokenRefreshView.as_view(), name="auth-refresh"),
    path("logout", views.LogoutView.as_view(), name="auth-logout"),
    path("me", views.MeView.as_view(), name="auth-me"),
    path("profile", views.ProfileView.as_view(), name="auth-profile"),
    path("change-password", views.ChangePasswordView.as_view(), name="auth-change-password"),
    path("forgot-password", views.ForgotPasswordView.as_view(), name="auth-forgot-password"),
    path("reset-password", views.ResetPasswordConfirmView.as_view(), name="api-password-reset-confirm"),
    path("register-teacher", views.RegisterTeacherView.as_view(), name="auth-register-teacher"),
    path("teachers", views.TeacherListView.as_view(), name="auth-teachers"),
]