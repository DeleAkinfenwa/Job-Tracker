from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .demo import is_demo_user

User = get_user_model()


# The profile returned by /api/auth/me/; only the name can be changed.
class UserSerializer(serializers.ModelSerializer):
    is_demo = serializers.SerializerMethodField(help_text="True for the shared demo account, which can't be edited.")

    class Meta:
        model = User
        fields = ("id", "email", "full_name", "date_joined", "is_demo")
        read_only_fields = ("id", "email", "date_joined")

    # Flags the shared demo account so the frontend can show a banner.
    def get_is_demo(self, user) -> bool:
        return is_demo_user(user)


# Validates sign-up data and creates the account; the password is never sent back.
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ("id", "email", "full_name", "password")
        read_only_fields = ("id",)

    # Store emails in lowercase and refuse ones that are already registered.
    def validate_email(self, value: str) -> str:
        value = value.lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        # Run Django's password validators (length, common passwords, similarity to email, etc.)
        validate_password(attrs["password"], user=User(email=attrs.get("email")))
        return attrs

    # create_user hashes the password before saving.
    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
