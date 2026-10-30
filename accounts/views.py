from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied

from .demo import is_demo_user
from .serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    """Create an account. Then get a token from `/api/auth/token/`."""

    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    """View or update the logged-in user's profile."""

    serializer_class = UserSerializer
    http_method_names = ["get", "patch"]

    # Always the logged-in user, so nobody can view or edit someone else's profile.
    def get_object(self):
        return self.request.user

    # Block profile edits on the shared demo account.
    def perform_update(self, serializer):
        if is_demo_user(self.request.user):
            raise PermissionDenied("The demo account's profile can't be changed.")
        serializer.save()
