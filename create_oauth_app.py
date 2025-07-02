#!/usr/bin/env python
import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socipedia.settings')
django.setup()

from oauth2_provider.models import Application

# Create OAuth2 application for React frontend
application = Application.objects.create(
    name="Socipedia React Frontend",
    user=None,
    client_type=Application.CLIENT_PUBLIC,
    authorization_grant_type=Application.GRANT_AUTHORIZATION_CODE,
    client_id="socipedia-react-client",
    skip_authorization=True,  # Skip authorization for same-party applications
)

print(f"OAuth2 Application created:")
print(f"Client ID: {application.client_id}")
print(f"Client Secret: {application.client_secret}")
print(f"Client Type: {application.client_type}")
print(f"Grant Type: {application.authorization_grant_type}")
