from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="full_name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "name",
            "role",
            "title",
            "mobile",
        ]
        read_only_fields = ["id", "role"]


class TeacherRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "title",
            "mobile",
        ]
        extra_kwargs = {"email": {"required": True}}

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Username is already taken.")
        return value

    def validate_email(self, value):
        value = (value or "").strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Email is already registered.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.role = User.Role.TEACHER
        user.set_password(password)
        user.save()
        return user


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "title", "mobile", "email"]
        extra_kwargs = {"email": {"required": False}}

    def validate_email(self, value):
        value = (value or "").strip().lower()
        existing = User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError("Email is already registered.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        # Only normalise; never validate existence here so the endpoint cannot
        # be used to enumerate which email addresses have accounts.
        return value.strip().lower()


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)

    def validate(self, attrs):
        email = attrs["email"].strip().lower()
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            raise serializers.ValidationError({"email": "Unknown account."})
        if not user.is_password_reset_token_valid(attrs["token"]):
            raise serializers.ValidationError(
                {"token": "This reset link is invalid or has expired."}
            )
        attrs["user"] = user
        return attrs


class RoleTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT login supporting username OR email, plus a 'remember_me' flag
    that extends the refresh-token lifetime for long-lived sessions."""

    remember_me = serializers.BooleanField(default=False, required=False)

    def validate(self, attrs):
        identifier = str(attrs.get("username", "")).strip().lower()
        if identifier:
            user = User.objects.filter(username__iexact=identifier).first()
            if user is None:
                user = User.objects.filter(email__iexact=identifier).first()
            if user is not None:
                # Re-point authenticate() at the resolved username.
                attrs["username"] = user.username
        data = super().validate(attrs)
        data["remember_me"] = bool(attrs.get("remember_me", False))
        data["user"] = UserSerializer(self.user).data
        return data

    def get_token(self, user):
        token = super().get_token(user)
        if bool((self.initial_data or {}).get("remember_me", False)):
            token.set_exp(lifetime=settings.REMEMBER_ME_REFRESH_LIFETIME)
        return token