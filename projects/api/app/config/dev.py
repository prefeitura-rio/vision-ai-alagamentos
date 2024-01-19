# -*- coding: utf-8 -*-
from . import getenv_list_or_action, getenv_or_action
from .base import *  # noqa: F401, F403

# Database configuration
DATABASE_URL = getenv_or_action(
    "DATABASE_URL", default="postgres://postgres:postgres@localhost:5432/postgres"
)

# CORS configuration
ALLOWED_ORIGINS = getenv_list_or_action("ALLOWED_ORIGINS", default=["*"])
ALLOWED_ORIGINS_REGEX = None
ALLOWED_METHODS = getenv_list_or_action("ALLOWED_METHODS", default=["*"])
ALLOWED_HEADERS = getenv_list_or_action("ALLOWED_HEADERS", default=["*"])
ALLOW_CREDENTIALS = getenv_or_action("ALLOW_CREDENTIALS", default="true").lower() == "true"
