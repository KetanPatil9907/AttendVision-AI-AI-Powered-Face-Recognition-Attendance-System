from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.urls import reverse
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from accounts.serializers import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    ProfileUpdateSerializer,
    ResetPasswordSerializer,
    RoleTokenObtainPairSerializer,
    TeacherRegisterSerializer,
    UserSerializer,
)

User = get_user_model()


class LoginView(TokenObtainPairView):
    serializer_class = RoleTokenObtainPairSerializer


class LogoutView(APIView):
    """Blacklist the refresh token on logout."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            token = RefreshToken(request.data.get("refresh", ""))
            token.blacklist()
        except Exception:
            # Token already invalid/expired - still treat logout as successful.
            pass
        return Response({"message": "Logged out successfully."})


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class RegisterTeacherView(generics.CreateAPIView):
    """Admin-only: create a new Teacher account."""

    permission_classes = [permissions.IsAdminUser]
    queryset = User.objects.all()
    serializer_class = TeacherRegisterSerializer


class TeacherListView(generics.ListAPIView):
    """Admin-only: list teacher accounts."""

    permission_classes = [permissions.IsAdminUser]
    queryset = User.objects.filter(role=User.Role.TEACHER)
    serializer_class = UserSerializer


class ProfileView(generics.RetrieveUpdateAPIView):
    """Logged-in teacher updates their own profile."""

    serializer_class = ProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"message": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response({"message": "Password changed successfully."})


class ForgotPasswordView(APIView):
    """Anonymous: request a password-reset link sent to the account email.

    In development the email is printed to the console (console email backend)
    or written to the mail directory. The link contains a short-lived signed
    token and must be redeemed within the token timeout.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email).first()
        reset_url = request.build_absolute_uri(reverse("api-password-reset-confirm"))
        if user is not None:
            token = user.password_reset_token()
            send_mail(
                subject="Reset your Smart Attendance System password",
                message=(
                    f"Hi {user.full_name},\n\n"
                    "We received a request to reset your Smart Attendance password.\n"
                    f"Open the link below within 24 hours to choose a new password:\n\n"
                    f"{reset_url}?email={email}&token={token}\n\n"
                    "If you did not request this, you can ignore this email.\n\n"
                    "Smart Attendance System"
                ),
                from_email=None,
                recipient_list=[email],
                fail_silently=True,
            )
        # Always respond the same way to avoid leaking which emails exist.
        return Response(
            {
                "message": (
                    "If an account exists for this email, a password reset "
                    "link has been sent."
                )
            }
        )


class ResetPasswordConfirmView(APIView):
    """Anonymous: redeem a reset token and set a new password."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response({"message": "Password reset successfully. You can now sign in."})