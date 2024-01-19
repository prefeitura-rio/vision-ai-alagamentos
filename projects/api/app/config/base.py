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
