# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime
from os import getenv
from uuid import UUID

import pytest
from httpx import AsyncClient
from loguru import logger
from tortoise import Tortoise

from app.db import TORTOISE_ORM
from app.main import app
from app.models import (
    Agent,
    Camera,
    Identification,
    Label,
    Object,
    Prompt,
    PromptObject,
    Snapshot,
)


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="session")
async def context():
    yield {}


@pytest.fixture(scope="session", autouse=True)
async def initialize_tests(context: dict):
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()
    logger.info("Tortoise-ORM schemas generated")
    await Agent.all().delete()
    await Camera.all().delete()
    await Identification.all().delete()
    await Label.all().delete()
    await Object.all().delete()
    await Prompt.all().delete()
    agent_data = [
        {
            "name": "Agent 1",
            "slug": "agent-1",
            "auth_sub": "auth-sub-1",
        },
    ]
    agents = []
    for agent in agent_data:
        agents.append(await Agent.create(**agent))
    camera_data = [
        {
            "id": "0001",
            "name": "Camera 1",
            "rtsp_url": "rtsp://one",
            "update_interval": 30,
            "latitude": 1.0,
            "longitude": 1.0,
        },
        {
            "id": "0002",
            "name": "Camera 2",
            "rtsp_url": "rtsp://two",
            "update_interval": 30,
            "latitude": 2.0,
            "longitude": 2.0,
        },
        {
            "id": "0003",
            "name": "Camera 3",
            "rtsp_url": "rtsp://three",
            "update_interval": 30,
            "latitude": 3.0,
            "longitude": 3.0,
        },
    ]
    cameras = []
    for camera in camera_data:
        cameras.append(await Camera.create(**camera))

    object_data = [
        {
            "name": "Person",
            "slug": "person",
            "title": "Tem pessoas",
            "question": "Tem pessoas na imagem?",
            "explanation": "A imagem contém pessoas",
        },
        {
            "name": "Car",
            "slug": "car",
            "title": "Tem carros",
            "question": "Tem carros na imagem?",
            "explanation": "A imagem contém somente o rosto de uma pessoa",
        },
        {
            "name": "Bicycle",
            "slug": "bicycle",
            "title": "Tem bicicletas",
            "question": "Tem bicicletas na imagem?",
            "explanation": "A imagem contém bicicletas",
        },
    ]
    objects = []
    for object in object_data:
        objects.append(await Object.create(**object))

    label_data = [
        {
            "object": objects[0],
            "value": "found",
            "criteria": "There is a person in the frame",
            "identification_guide": "Description",
            "text": "Achou",
            "order": 1,
        },
        {
            "object": objects[0],
            "value": "not-found",
            "criteria": "There is no person in the frame",
            "identification_guide": "Description",
            "text": "Não Achou",
            "order": 2,
        },
        {
            "object": objects[1],
            "value": "found",
            "criteria": "There is a car in the frame",
            "identification_guide": "Description",
            "text": "Achou",
            "order": 1,
        },
        {
            "object": objects[1],
            "value": "not-found",
            "criteria": "There is no car in the frame",
            "identification_guide": "Description",
            "text": "Não achou",
            "order": 2,
        },
        {
            "object": objects[2],
            "value": "found",
            "criteria": "There is a bicycle in the frame",
            "identification_guide": "Description",
            "text": "Achou",
            "order": 1,
        },
        {
            "object": objects[2],
            "value": "not-found",
            "criteria": "There is no bicycle in the frame",
            "identification_guide": "Description",
            "text": "Não achou",
            "order": 2,
        },
    ]
    labels = []
    for label in label_data:
        labels.append(await Label.create(**label))

    prompt_data = [
        {
            "name": "Prompt 1",
            "model": "dalle-mini",
            "prompt_text": "Prompt 1 text",
            "max_output_token": 100,
            "temperature": 0.5,
            "top_k": 0,
            "top_p": 0.9,
        },
        {
            "name": "Prompt 2",
            "model": "dalle-mini",
            "prompt_text": "Prompt 2 text",
            "max_output_token": 100,
            "temperature": 0.5,
            "top_k": 0,
            "top_p": 0.9,
        },
        {
            "name": "Prompt 3",
            "model": "dalle-mini",
            "prompt_text": "Prompt 3 text \n {objects_table_md} \n\n\n {output_schema} \n\n\n {output_example}",  # noqa
            "max_output_token": 100,
            "temperature": 0.5,
            "top_k": 0,
            "top_p": 0.9,
        },
    ]
    prompts = []
    for prompt in prompt_data:
        prompts.append(await Prompt.create(**prompt))

    for i, prompt in enumerate(prompts):
        for j, object in enumerate(objects[: i + 1]):
            await PromptObject.create(prompt=prompt, object=object, order=j)

    snapshot_data = [
        {
            "public_url": "http://example.com/1",
            "timestamp": datetime.now(),
            "camera": cameras[0],
        },
        {
            "public_url": "http://example.com/2",
            "timestamp": datetime.now(),
            "camera": cameras[0],
        },
        {
            "public_url": "http://example.com/3",
            "timestamp": datetime.now(),
            "camera": cameras[0],
        },
        {
            "public_url": "http://example.com/4",
            "timestamp": datetime.now(),
            "camera": cameras[0],
        },
        {
            "public_url": "http://example.com/5",
            "timestamp": datetime.now(),
            "camera": cameras[1],
        },
        {
            "public_url": "http://example.com/6",
            "timestamp": datetime.now(),
            "camera": cameras[1],
        },
        {
            "public_url": "http://example.com/7",
            "timestamp": datetime.now(),
            "camera": cameras[1],
        },
        {
            "public_url": "http://example.com/8",
            "timestamp": datetime.now(),
            "camera": cameras[1],
        },
        {
            "public_url": "http://example.com/9",
            "timestamp": datetime.now(),
            "camera": cameras[2],
        },
        {
            "public_url": "http://example.com/10",
            "timestamp": datetime.now(),
            "camera": cameras[2],
        },
        {
            "public_url": "http://example.com/11",
            "timestamp": datetime.now(),
            "camera": cameras[2],
        },
        {
            "public_url": "http://example.com/12",
            "timestamp": datetime.now(),
            "camera": cameras[2],
        },
    ]
    snapshots = []
    for snapshot in snapshot_data:
        snapshots.append(await Snapshot.create(**snapshot))

    identification_data = [
        {
            "snapshot": snapshots[0],
            "label": labels[0],
            "label_explanation": "There is a person in the frame",
            "timestamp": datetime.now(),
        },
        {
            "snapshot": snapshots[0],
            "label": labels[1],
            "label_explanation": "There is no person in the frame",
            "timestamp": datetime.now(),
        },
        {
            "snapshot": snapshots[1],
            "label": labels[2],
            "label_explanation": "There is a car in the frame",
            "timestamp": datetime.now(),
        },
        {
            "snapshot": snapshots[1],
            "label": labels[3],
            "label_explanation": "There is no car in the frame",
            "timestamp": datetime.now(),
        },
        {
            "snapshot": snapshots[2],
            "label": labels[4],
            "label_explanation": "There is a bicycle in the frame",
            "timestamp": datetime.now(),
        },
        {
            "snapshot": snapshots[2],
            "label": labels[5],
            "label_explanation": "There is no bicycle in the frame",
            "timestamp": datetime.now(),
        },
    ]

    identifications_id: list[UUID] = []
    for identification in identification_data:
        new = await Identification.create(**identification)
        identifications_id.append(new.id)
    context["identifications_id"] = identifications_id
    logger.info("Test data initialized")

    await Tortoise.close_connections()
    yield


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
                "scope": "profile",
            },
        )
        yield response.json()["access_token"]


@pytest.fixture(scope="session")
async def authorization_header(access_token):
    yield {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(scope="session")
async def image_base64():
    yield "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"  # noqa
