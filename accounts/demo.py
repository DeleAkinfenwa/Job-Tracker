"""The shared demo account that portfolio visitors log in with.

Its data is reset every time the server starts (see the Dockerfile), and its
profile can't be edited, so one visitor can't spoil the demo for the next.
"""

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "Demo-password-2026"


# True if this is the shared demo account.
def is_demo_user(user) -> bool:
    return getattr(user, "email", None) == DEMO_EMAIL
