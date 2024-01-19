# -*- coding: utf-8 -*-
import sys

import sentry_sdk
from app import config
from app.db import TORTOISE_ORM
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from tortoise.contrib.fastapi import register_tortoise

# from app.routers import ... # TODO: import routers

logger.remove()
logger.add(sys.stdout, level=config.LOG_LEVEL)

if config.SENTRY_ENABLE:
    sentry_sdk.init(
        dsn=config.SENTRY_DSN,
        traces_sample_rate=0,
        environment=config.SENTRY_ENVIRONMENT,
    )

app = FastAPI(
    title="Unificador de Prontuários - SMSRio",
)

logger.debug("Configuring CORS with the following settings:")
allow_origins = config.ALLOWED_ORIGINS if config.ALLOWED_ORIGINS else ()
logger.debug(f"ALLOWED_ORIGINS: {allow_origins}")
allow_origin_regex = config.ALLOWED_ORIGINS_REGEX if config.ALLOWED_ORIGINS_REGEX else None
logger.debug(f"ALLOWED_ORIGINS_REGEX: {allow_origin_regex}")
logger.debug(f"ALLOWED_METHODS: {config.ALLOWED_METHODS}")
logger.debug(f"ALLOWED_HEADERS: {config.ALLOWED_HEADERS}")
logger.debug(f"ALLOW_CREDENTIALS: {config.ALLOW_CREDENTIALS}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=allow_origin_regex,
    allow_methods=config.ALLOWED_METHODS,
    allow_headers=config.ALLOWED_HEADERS,
    allow_credentials=config.ALLOW_CREDENTIALS,
)

# app.include_router(users.router) # TODO: include routers

register_tortoise(
    app,
    config=TORTOISE_ORM,
    generate_schemas=False,
    add_exception_handlers=True,
)
