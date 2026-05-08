import base64
import os


def generate_secret_bytes(length: int = 32) -> str:
    """Returns a URL-safe base64 secret string."""

    return base64.urlsafe_b64encode(os.urandom(length)).decode("utf-8").rstrip("=")
