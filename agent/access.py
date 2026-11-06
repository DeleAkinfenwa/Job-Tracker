"""Who may use the resume agent.

The agent spends the owner's Anthropic credit, so it is locked to the emails in the
AGENT_OWNER_EMAILS setting. Everyone else, including the shared demo account, gets a
404 from every agent endpoint, so the feature can't even be discovered.
"""

from django.conf import settings
from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission

from accounts.demo import is_demo_user


def owner_emails() -> set[str]:
    return {e.strip().lower() for e in settings.AGENT_OWNER_EMAILS if e.strip()}


# True if this user may use the resume agent.
def agent_enabled(user) -> bool:
    if not getattr(user, "is_authenticated", False) or is_demo_user(user):
        return False
    return str(getattr(user, "email", "")).lower() in owner_emails()


class IsAgentOwner(BasePermission):
    """Lets only the configured owner in. Other logged-in accounts get 404, not 403."""

    def has_permission(self, request, view):
        # Logged-out requests get the usual 401, so the website knows to refresh its login.
        if not request.user or not request.user.is_authenticated:
            return False
        if not agent_enabled(request.user):
            raise NotFound()
        return True
