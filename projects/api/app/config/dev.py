# -*- coding: utf-8 -*-
from . import getenv_list_or_action, getenv_or_action
from .base import *  # noqa: F401, F403

# Database configuration
DATABASE_HOST = getenv_or_action("DATABASE_HOST", default="localhost")
DATABASE_PORT = getenv_or_action("DATABASE_PORT", default="5432")
DATABASE_USER = getenv_or_action("DATABASE_USER", default="postgres")
DATABASE_PASSWORD = getenv_or_action("DATABASE_PASSWORD", default="postgres")
DATABASE_NAME = getenv_or_action("DATABASE_NAME", default="postgres")

# CORS configuration
ALLOWED_ORIGINS = getenv_list_or_action("ALLOWED_ORIGINS", default=["*"])
ALLOWED_ORIGINS_REGEX = None
ALLOWED_METHODS = getenv_list_or_action("ALLOWED_METHODS", default=["*"])
ALLOWED_HEADERS = getenv_list_or_action("ALLOWED_HEADERS", default=["*"])
ALLOW_CREDENTIALS = getenv_or_action("ALLOW_CREDENTIALS", default="true").lower() == "true"
