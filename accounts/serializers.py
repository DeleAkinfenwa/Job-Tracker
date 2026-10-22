from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .demo import is_demo_user

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    is_demo = serializers.SerializerMethodField(help_text="True for the shared demo account, which can't be edited.")

    class Meta:
        model = User
        fields = ("id", "email", "full_name", "date_joined", "is_demo")
        read_only_fields = ("id", "email", "date_joined")

    def get_is_demo(self, user) -> bool:
        return is_demo_user(user)


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ("id", "email", "full_name", "password")
        read_only_fields = ("id",)

    def validate_email(self, value: str) -> str:
        value = value.lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        # Run Django's password validators (length, common passwords, similarity to email, etc.)
        validate_password(attrs["password"], user=User(email=attrs.get("email")))
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
