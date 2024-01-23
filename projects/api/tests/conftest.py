# -*- coding: utf-8 -*-
from os import getenv

import pytest
from app.db import TORTOISE_ORM
from app.main import app
from httpx import AsyncClient
from loguru import logger
from tortoise import Tortoise


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="session", autouse=True)
async def initialize_tests():
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()
    logger.info("Tortoise-ORM schemas generated")
    yield
    await Tortoise.close_connections()


@pytest.fixture(scope="session")
async def username():
    username_ = getenv("TEST_USERNAME")
    if not username_:
        raise ValueError("TEST_USERNAME environment variable is not set")

    yield username_


@pytest.fixture(scope="session")
async def password():
    password_ = getenv("TEST_PASSWORD")
    if not password_:
        raise ValueError("TEST_PASSWORD environment variable is not set")

    yield password_


@pytest.fixture(scope="session")
async def client_id():
    client_id_ = getenv("TEST_CLIENT_ID")
    if not client_id_:
        raise ValueError("TEST_CLIENT_ID environment variable is not set")

    yield client_id_


@pytest.fixture(scope="session")
async def client_secret():
    client_secret_ = getenv("TEST_CLIENT_SECRET")
    if not client_secret_:
        raise ValueError("TEST_CLIENT_SECRET environment variable is not set")

    yield client_secret_


@pytest.fixture(scope="session")
async def token_url():
    token_url_ = getenv("TEST_TOKEN_URL")
    if not token_url_:
        raise ValueError("TEST_TOKEN_URL environment variable is not set")

    yield token_url_


@pytest.fixture(scope="session")
async def access_token(
    username,
    password,
    client_id,
    client_secret,
    token_url,
):
    async with AsyncClient() as client:
        # Authenticate
        response = await client.post(
            token_url,
            data={
                "grant_type": "password",
                "username": username,
                "password": password,
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        yield response.json()["access_token"]


@pytest.fixture(scope="session")
async def authorization_header(access_token):
    yield {"Authorization": f"Bearer {access_token}"}
