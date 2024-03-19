# -*- coding: utf-8 -*-
import sys

import sentry_sdk
from app import config
from app.db import TORTOISE_ORM
from app.oidc import AuthError
from app.routers import agents, auth, cameras, identifications, objects, prompts
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_pagination import add_pagination
from loguru import logger
from starlette.responses import JSONResponse
from tortoise.contrib.fastapi import register_tortoise

logger.remove()
logger.add(sys.stdout, level=config.LOG_LEVEL)

if config.SENTRY_ENABLE:
    sentry_sdk.init(
        dsn=config.SENTRY_DSN,
        traces_sample_rate=0,
        environment=config.SENTRY_ENVIRONMENT,
    )

app = FastAPI(
    title="Vision AI API",
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

app.include_router(auth.router)
app.include_router(agents.router)
app.include_router(cameras.router)
app.include_router(objects.router)
app.include_router(prompts.router)
app.include_router(identifications.router)


register_tortoise(
    app,
    config=TORTOISE_ORM,
    generate_schemas=False,
    add_exception_handlers=True,
)

add_pagination(app)


FastAPICache.init(InMemoryBackend())


@app.exception_handler(AuthError)
def handle_auth_error(request: Request, ex: AuthError):
    return JSONResponse(status_code=ex.status_code, content=ex.error)
