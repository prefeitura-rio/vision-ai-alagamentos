# -*- coding: utf-8 -*-
from . import getenv_or_action

# Logging
LOG_LEVEL = getenv_or_action("LOG_LEVEL", default="INFO")

# Timezone configuration
TIMEZONE = "America/Sao_Paulo"

# Sentry
SENTRY_ENABLE = False
SENTRY_DSN = None
SENTRY_ENVIRONMENT = None

# OIDC
OIDC_CLIENT_ID = getenv_or_action("OIDC_CLIENT_ID")
OIDC_ISSUER_URL = getenv_or_action("OIDC_ISSUER_URL")
OIDC_TOKEN_URL = getenv_or_action("OIDC_TOKEN_URL")

# GCP
GCP_SERVICE_ACCOUNT_CREDENTIALS = getenv_or_action("GCP_SERVICE_ACCOUNT_CREDENTIALS", action="warn")
GCS_BUCKET_NAME = getenv_or_action("GCS_BUCKET_NAME", action="warn")
GCS_BUCKET_PATH_PREFIX = getenv_or_action("GCS_BUCKET_PATH_PREFIX", action="warn")
if GCS_BUCKET_PATH_PREFIX:
    GCS_BUCKET_PATH_PREFIX = GCS_BUCKET_PATH_PREFIX.rstrip("/")
