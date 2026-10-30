from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Manager for a user model that logs in with email instead of username."""

    use_in_migrations = True

    # Lets Django's login look users up by email, ignoring case.
    def get_by_natural_key(self, email):
        # emails are stored in lowercase so Ada@example.com must find ada@example.com
        return self.get(email__iexact=email.strip())

    # Shared by both create methods: checks the email, hashes the password and saves.
    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        user = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    # A regular user with no admin rights.
    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    # An admin user who can log in to /admin.
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("Superuser must have is_staff=True and is_superuser=True")
        return self._create_user(email, password, **extra_fields)


# A user account that logs in with email and password; there is no username.
class User(AbstractUser):
    username = None
    email = models.EmailField("email address", unique=True)
    full_name = models.CharField(max_length=255, blank=True)

    # Use the email as the login name, and ask for nothing else when creating an admin.
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    def __str__(self) -> str:
        return self.email
