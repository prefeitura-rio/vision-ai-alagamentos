# -*- coding: utf-8 -*-
from . import getenv_list_or_action, getenv_or_action
from .base import *  # noqa: F401, F403

# Logging
LOG_LEVEL = getenv_or_action("LOG_LEVEL", action="ignore", default="INFO")

# Database configuration
DATABASE_URL = getenv_or_action("DATABASE_URL", action="raise")

# Password hashing configuration
if getenv_or_action("PASSWORD_HASH_ALGORITHM", action="ignore"):
    PASSWORD_HASH_ALGORITHM = getenv_or_action("PASSWORD_HASH_ALGORITHM")
if getenv_or_action("PASSWORD_HASH_NUMBER_OF_ITERATIONS", action="ignore"):
    PASSWORD_HASH_NUMBER_OF_ITERATIONS = int(getenv_or_action("PASSWORD_HASH_NUMBER_OF_ITERATIONS"))

# Timezone configuration
if getenv_or_action("TIMEZONE", action="ignore"):
    TIMEZONE = getenv_or_action("TIMEZONE")

# CORS configuration
ALLOWED_ORIGINS = getenv_list_or_action("ALLOWED_ORIGINS", action="ignore")
ALLOWED_ORIGINS_REGEX = getenv_or_action("ALLOWED_ORIGINS_REGEX", action="ignore")
if not ALLOWED_ORIGINS and not ALLOWED_ORIGINS_REGEX:
    raise EnvironmentError("ALLOWED_ORIGINS or ALLOWED_ORIGINS_REGEX must be set.")
ALLOWED_METHODS = getenv_list_or_action("ALLOWED_METHODS", action="raise")
ALLOWED_HEADERS = getenv_list_or_action("ALLOWED_HEADERS", action="raise")
ALLOW_CREDENTIALS = getenv_or_action("ALLOW_CREDENTIALS", action="raise").lower() == "true"

# Sentry
SENTRY_ENABLE = getenv_or_action("SENTRY_ENABLE", action="ignore").lower() == "true"
if SENTRY_ENABLE:
    SENTRY_DSN = getenv_or_action("SENTRY_DSN", action="raise")
    SENTRY_ENVIRONMENT = getenv_or_action("SENTRY_ENVIRONMENT", action="raise")
