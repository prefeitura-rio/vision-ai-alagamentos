# -*- coding: utf-8 -*-
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
@pytest.mark.run(order=51)
async def test_get_identification(
    client: AsyncClient,
    authorization_header: dict,
):
    response = await client.get("/identifications", headers=authorization_header)

    assert response.status_code == 200
    assert "items" in response.json()
    assert "total" in response.json()
    assert "page" in response.json()
    assert "size" in response.json()
    assert "pages" in response.json()
    assert isinstance(response.json()["total"], int)
    assert isinstance(response.json()["page"], int)
    assert isinstance(response.json()["size"], int)
    assert response.json()["total"] == 7
    assert response.json()["page"] == 1
    assert response.json()["size"] == 100
    assert response.json()["pages"] == 1
    assert isinstance(response.json()["pages"], int)
    assert len(response.json()["items"]) == 7
    for item in response.json()["items"]:
        assert "id" in item
        assert "object" in item
        assert "title" in item
        assert "question" in item
        assert "explanation" in item
        assert "timestamp" in item
        assert "label" in item
        assert "label_explanation" in item
        assert "snapshot" in item
        assert "id" in item["snapshot"]
        assert "camera_id" in item["snapshot"]
        assert "image_url" in item["snapshot"]
        assert "timestamp" in item["snapshot"]
        assert isinstance(item["id"], str)
        assert isinstance(item["object"], str)
        assert isinstance(item["question"], str)
        assert isinstance(item["title"], str)
        assert isinstance(item["explanation"], str)
        assert isinstance(item["timestamp"], str)
        assert isinstance(item["label"], str)
        assert isinstance(item["label_explanation"], str)
        assert isinstance(item["snapshot"]["id"], str)
        assert isinstance(item["snapshot"]["camera_id"], str)
        assert isinstance(item["snapshot"]["image_url"], str)
        assert isinstance(item["snapshot"]["timestamp"], str)


@pytest.mark.anyio
@pytest.mark.run(order=52)
async def test_create_marker_identifications(
    client: AsyncClient, authorization_header: dict, context: dict
):
    response = await client.post(
        "/identifications/marker",
        headers=authorization_header,
        json={
            "identifications_id": [str(id) for id in context["identifications_id"][:2]],
        },
    )

    assert response.status_code == 200
    assert "count" in response.json()
    assert "ids" in response.json()
    assert isinstance(response.json()["count"], int)
    assert isinstance(response.json()["ids"], list)
    assert len(response.json()["ids"]) == 2
    for item in response.json()["ids"]:
        assert isinstance(item, str)


@pytest.mark.anyio
@pytest.mark.run(order=53)
async def test_add_tags_marker_identifications(
    client: AsyncClient, authorization_header: dict, context: dict
):
    response = await client.post(
        "/identifications/marker",
        headers=authorization_header,
        json={
            "identifications_id": [str(id) for id in context["identifications_id"][:2]],
            "snapshots_id": [str(context["test_snapshot_id"])],
            "tags": ["tag1", "tag2"],
        },
    )

    assert response.status_code == 200
    assert "count" in response.json()
    assert "ids" in response.json()
    assert isinstance(response.json()["count"], int)
    assert isinstance(response.json()["ids"], list)
    assert len(response.json()["ids"]) == 3
    for item in response.json()["ids"]:
        assert isinstance(item, str)


@pytest.mark.anyio
@pytest.mark.run(order=54)
async def test_create_marker_with_tag_identifications(
    client: AsyncClient, authorization_header: dict, context: dict
):
    response = await client.post(
        "/identifications/marker",
        headers=authorization_header,
        json={
            "identifications_id": [str(id) for id in context["identifications_id"][:4]],
            "tags": ["tag3", "tag4"],
        },
    )

    assert response.status_code == 200
    assert "count" in response.json()
    assert "ids" in response.json()
    assert isinstance(response.json()["count"], int)
    assert isinstance(response.json()["ids"], list)
    assert len(response.json()["ids"]) == 4
    for item in response.json()["ids"]:
        assert isinstance(item, str)


@pytest.mark.anyio
@pytest.mark.run(order=55)
async def test_get_all_ai_identification_1(
    client: AsyncClient,
    authorization_header: dict,
):
    response = await client.get("/identifications/ai", headers=authorization_header)

    assert response.status_code == 200
    assert "items" in response.json()
    assert "total" in response.json()
    assert "page" in response.json()
    assert "size" in response.json()
    assert "pages" in response.json()
    assert isinstance(response.json()["total"], int)
    assert isinstance(response.json()["page"], int)
    assert isinstance(response.json()["size"], int)
    assert response.json()["total"] == 5
    assert response.json()["page"] == 1
    assert response.json()["size"] == 100
    assert response.json()["pages"] == 1
    assert isinstance(response.json()["pages"], int)
    assert len(response.json()["items"]) == 5
    for item in response.json()["items"]:
        assert "id" in item
        assert "object" in item
        assert "title" in item
        assert "question" in item
        assert "explanation" in item
        assert "timestamp" in item
        assert "label" in item
        assert "label_explanation" in item
        assert "snapshot" in item
        assert "id" in item["snapshot"]
        assert "camera_id" in item["snapshot"]
        assert "image_url" in item["snapshot"]
        assert "timestamp" in item["snapshot"]
        assert isinstance(item["id"], str)
        assert isinstance(item["object"], str)
        assert isinstance(item["question"], str)
        assert isinstance(item["title"], str)
        assert isinstance(item["explanation"], str)
        assert isinstance(item["timestamp"], str)
        assert isinstance(item["label"], str)
        assert isinstance(item["label_explanation"], str)
        assert isinstance(item["snapshot"]["id"], str)
        assert isinstance(item["snapshot"]["camera_id"], str)
        assert isinstance(item["snapshot"]["image_url"], str)
        assert isinstance(item["snapshot"]["timestamp"], str)


@pytest.mark.anyio
@pytest.mark.run(order=56)
async def test_get_all_ai_identification_2(
    client: AsyncClient,
    authorization_header: dict,
):
    response = await client.get("/identifications/ai/all", headers=authorization_header)

    assert response.status_code == 200
    assert "items" in response.json()
    assert "total" in response.json()
    assert "page" in response.json()
    assert "size" in response.json()
    assert "pages" in response.json()
    assert isinstance(response.json()["total"], int)
    assert isinstance(response.json()["page"], int)
    assert isinstance(response.json()["size"], int)
    assert response.json()["total"] == 5
    assert response.json()["page"] == 1
    assert response.json()["size"] == 100
    assert response.json()["pages"] == 1
    assert isinstance(response.json()["pages"], int)
    assert len(response.json()["items"]) == 5
    for item in response.json()["items"]:
        assert "id" in item
        assert "object" in item
        assert "title" in item
        assert "question" in item
        assert "explanation" in item
        assert "timestamp" in item
        assert "label" in item
        assert "label_explanation" in item
        assert "snapshot" in item
        assert "id" in item["snapshot"]
        assert "camera_id" in item["snapshot"]
        assert "image_url" in item["snapshot"]
        assert "timestamp" in item["snapshot"]
        assert isinstance(item["id"], str)
        assert isinstance(item["object"], str)
        assert isinstance(item["question"], str)
        assert isinstance(item["title"], str)
        assert isinstance(item["explanation"], str)
        assert isinstance(item["timestamp"], str)
        assert isinstance(item["label"], str)
        assert isinstance(item["label_explanation"], str)
        assert isinstance(item["snapshot"]["id"], str)
        assert isinstance(item["snapshot"]["camera_id"], str)
        assert isinstance(item["snapshot"]["image_url"], str)
        assert isinstance(item["snapshot"]["timestamp"], str)


@pytest.mark.anyio
@pytest.mark.run(order=57)
async def test_create_human_identification_1(
    client: AsyncClient,
    authorization_header: dict,
    context: dict,
):
    response = await client.post(
        "/identifications",
        headers=authorization_header,
        json={
            "identification_id": context["test_identification_id"],
            "label": context["test_label_value"],
        },
    )

    assert response.status_code == 200
    assert "id" in response.json()
    assert "object" in response.json()
    assert "title" in response.json()
    assert "question" in response.json()
    assert "explanation" in response.json()
    assert "timestamp" in response.json()
    assert "label" in response.json()
    assert "label_explanation" in response.json()
    assert "snapshot" in response.json()
    assert "id" in response.json()["snapshot"]
    assert "camera_id" in response.json()["snapshot"]
    assert "image_url" in response.json()["snapshot"]
    assert "timestamp" in response.json()["snapshot"]
    assert isinstance(response.json()["id"], str)
    assert isinstance(response.json()["object"], str)
    assert isinstance(response.json()["title"], str)
    assert isinstance(response.json()["question"], str)
    assert isinstance(response.json()["explanation"], str)
    assert isinstance(response.json()["timestamp"], str)
    assert isinstance(response.json()["label"], str)
    assert isinstance(response.json()["label_explanation"], str)
    assert isinstance(response.json()["snapshot"]["id"], str)
    assert isinstance(response.json()["snapshot"]["camera_id"], str)
    assert isinstance(response.json()["snapshot"]["image_url"], str)
    assert isinstance(response.json()["snapshot"]["timestamp"], str)
    assert response.json()["object"] == context["test_object_slug"]
    assert response.json()["label"] == context["test_label_value"]
    assert response.json()["snapshot"]["id"] == context["test_snapshot_id"]


@pytest.mark.anyio
@pytest.mark.run(order=57)
async def test_create_human_identification_2(
    client: AsyncClient,
    authorization_header: dict,
    context: dict,
):
    response = await client.post(
        "/identifications",
        headers=authorization_header,
        json={
            "identification_id": str(context["identifications_id"][5]),
            "label": "found",
        },
    )

    assert response.status_code == 200
    assert "id" in response.json()
    assert "object" in response.json()
    assert "title" in response.json()
    assert "question" in response.json()
    assert "explanation" in response.json()
    assert "timestamp" in response.json()
    assert "label" in response.json()
    assert "label_explanation" in response.json()
    assert "snapshot" in response.json()
    assert "id" in response.json()["snapshot"]
    assert "camera_id" in response.json()["snapshot"]
    assert "image_url" in response.json()["snapshot"]
    assert "timestamp" in response.json()["snapshot"]
    assert isinstance(response.json()["id"], str)
    assert isinstance(response.json()["object"], str)
    assert isinstance(response.json()["title"], str)
    assert isinstance(response.json()["question"], str)
    assert isinstance(response.json()["explanation"], str)
    assert isinstance(response.json()["timestamp"], str)
    assert isinstance(response.json()["label"], str)
    assert isinstance(response.json()["label_explanation"], str)
    assert isinstance(response.json()["snapshot"]["id"], str)
    assert isinstance(response.json()["snapshot"]["camera_id"], str)
    assert isinstance(response.json()["snapshot"]["image_url"], str)
    assert isinstance(response.json()["snapshot"]["timestamp"], str)


@pytest.mark.anyio
@pytest.mark.run(order=58)
async def test_recreate_human_identification(
    client: AsyncClient,
    authorization_header: dict,
    context: dict,
):
    response = await client.post(
        "/identifications",
        headers=authorization_header,
        json={
            "identification_id": str(context["identifications_id"][5]),
            "label": "not-found",
        },
    )

    assert response.status_code == 200
    assert "id" in response.json()
    assert "object" in response.json()
    assert "title" in response.json()
    assert "question" in response.json()
    assert "explanation" in response.json()
    assert "timestamp" in response.json()
    assert "label" in response.json()
    assert "label_explanation" in response.json()
    assert "snapshot" in response.json()
    assert "id" in response.json()["snapshot"]
    assert "camera_id" in response.json()["snapshot"]
    assert "image_url" in response.json()["snapshot"]
    assert "timestamp" in response.json()["snapshot"]
    assert isinstance(response.json()["id"], str)
    assert isinstance(response.json()["object"], str)
    assert isinstance(response.json()["title"], str)
    assert isinstance(response.json()["question"], str)
    assert isinstance(response.json()["explanation"], str)
    assert isinstance(response.json()["timestamp"], str)
    assert isinstance(response.json()["label"], str)
    assert isinstance(response.json()["label_explanation"], str)
    assert isinstance(response.json()["snapshot"]["id"], str)
    assert isinstance(response.json()["snapshot"]["camera_id"], str)
    assert isinstance(response.json()["snapshot"]["image_url"], str)
    assert isinstance(response.json()["snapshot"]["timestamp"], str)


@pytest.mark.anyio
@pytest.mark.run(order=59)
async def test_get_ai_identification(client: AsyncClient, authorization_header: dict):
    response = await client.get("/identifications/ai", headers=authorization_header)

    assert response.status_code == 200
    assert "items" in response.json()
    assert "total" in response.json()
    assert "page" in response.json()
    assert "size" in response.json()
    assert "pages" in response.json()
    assert isinstance(response.json()["total"], int)
    assert isinstance(response.json()["page"], int)
    assert isinstance(response.json()["size"], int)
    assert response.json()["total"] == 4
    assert response.json()["page"] == 1
    assert response.json()["size"] == 100
    assert response.json()["pages"] == 1
    assert isinstance(response.json()["pages"], int)
    assert len(response.json()["items"]) == 4
    for item in response.json()["items"]:
        assert "id" in item
        assert "object" in item
        assert "title" in item
        assert "question" in item
        assert "explanation" in item
        assert "timestamp" in item
        assert "label" in item
        assert "label_explanation" in item
        assert "snapshot" in item
        assert "id" in item["snapshot"]
        assert "camera_id" in item["snapshot"]
        assert "image_url" in item["snapshot"]
        assert "timestamp" in item["snapshot"]
        assert isinstance(item["id"], str)
        assert isinstance(item["object"], str)
        assert isinstance(item["title"], str)
        assert isinstance(item["question"], str)
        assert isinstance(item["explanation"], str)
        assert isinstance(item["timestamp"], str)
        assert isinstance(item["label"], str)
        assert isinstance(item["label_explanation"], str)
        assert isinstance(item["snapshot"]["id"], str)
        assert isinstance(item["snapshot"]["camera_id"], str)
        assert isinstance(item["snapshot"]["image_url"], str)
        assert isinstance(item["snapshot"]["timestamp"], str)


@pytest.mark.anyo
@pytest.mark.run(order=60)
async def test_create_hide(client: AsyncClient, authorization_header: dict, context: dict):
    response = await client.post(
        "/identifications/hide",
        headers=authorization_header,
        json={
            "identifications_id": [
                str(identification) for identification in context["identifications_id"]
            ]
        },
    )

    assert response.status_code == 200
    assert "count" in response.json()
    assert "ids" in response.json()
    assert isinstance(response.json()["count"], int)
    assert isinstance(response.json()["ids"], list)
    assert len(response.json()["ids"]) == 6
    for id in response.json()["ids"]:
        assert isinstance(id, str)


@pytest.mark.anyo
@pytest.mark.run(order=61)
async def test_get_hide(client: AsyncClient, authorization_header: dict):
    response = await client.get("/identifications/hide", headers=authorization_header)

    assert response.status_code == 200
    assert len(response.json()) == 6
    for identification in response.json():
        assert "id" in identification
        assert "object" in identification
        assert "title" in identification
        assert "question" in identification
        assert "explanation" in identification
        assert "timestamp" in identification
        assert "label" in identification
        assert "label_explanation" in identification
        assert "snapshot" in identification
        assert "id" in identification["snapshot"]
        assert "camera_id" in identification["snapshot"]
        assert "image_url" in identification["snapshot"]
        assert "timestamp" in identification["snapshot"]
        assert isinstance(identification["id"], str)
        assert isinstance(identification["object"], str)
        assert isinstance(identification["title"], str)
        assert isinstance(identification["question"], str)
        assert isinstance(identification["explanation"], str)
        assert isinstance(identification["timestamp"], str)
        assert isinstance(identification["label"], str)
        assert isinstance(identification["label_explanation"], str)
        assert isinstance(identification["snapshot"]["id"], str)
        assert isinstance(identification["snapshot"]["camera_id"], str)
        assert isinstance(identification["snapshot"]["image_url"], str)
        assert isinstance(identification["snapshot"]["timestamp"], str)


@pytest.mark.anyio
@pytest.mark.run(order=62)
async def test_get_all_ai_identification_3(
    client: AsyncClient,
    authorization_header: dict,
):
    response = await client.get("/identifications/ai/all", headers=authorization_header)

    assert response.status_code == 200
    assert "items" in response.json()
    assert "total" in response.json()
    assert "page" in response.json()
    assert "size" in response.json()
    assert "pages" in response.json()
    assert isinstance(response.json()["total"], int)
    assert isinstance(response.json()["page"], int)
    assert isinstance(response.json()["size"], int)
    assert response.json()["total"] == 6
    assert response.json()["page"] == 1
    assert response.json()["size"] == 100
    assert response.json()["pages"] == 1
    assert isinstance(response.json()["pages"], int)
    assert len(response.json()["items"]) == 6
    for item in response.json()["items"]:
        assert "id" in item
        assert "object" in item
        assert "title" in item
        assert "question" in item
        assert "explanation" in item
        assert "timestamp" in item
        assert "label" in item
        assert "label_explanation" in item
        assert "snapshot" in item
        assert "id" in item["snapshot"]
        assert "camera_id" in item["snapshot"]
        assert "image_url" in item["snapshot"]
        assert "timestamp" in item["snapshot"]
        assert isinstance(item["id"], str)
        assert isinstance(item["object"], str)
        assert isinstance(item["question"], str)
        assert isinstance(item["title"], str)
        assert isinstance(item["explanation"], str)
        assert isinstance(item["timestamp"], str)
        assert isinstance(item["label"], str)
        assert isinstance(item["label_explanation"], str)
        assert isinstance(item["snapshot"]["id"], str)
        assert isinstance(item["snapshot"]["camera_id"], str)
        assert isinstance(item["snapshot"]["image_url"], str)
        assert isinstance(item["snapshot"]["timestamp"], str)


@pytest.mark.anyio
@pytest.mark.run(order=71)
async def test_delete_marker_identifications(
    client: AsyncClient, authorization_header: dict, context: dict
):
    # client.delete dont support body request: https://github.com/encode/httpx/discussions/1587
    response = await client.request(
        "DELETE",
        "/identifications/marker",
        headers=authorization_header,
        json={
            "identifications_id": [str(id) for id in context["identifications_id"]],
            "snapshots_id": [str(context["test_snapshot_id"])],
        },
    )

    assert response.status_code == 200
    assert "count" in response.json()
    assert "ids" in response.json()
    assert isinstance(response.json()["count"], int)
    assert isinstance(response.json()["ids"], list)
    assert len(response.json()["ids"]) == 7
    for item in response.json()["ids"]:
        assert isinstance(item, str)


@pytest.mark.anyio
@pytest.mark.run(order=72)
async def test_get_ai_identification_after_delete(client: AsyncClient, authorization_header: dict):
    response = await client.get("/identifications/ai", headers=authorization_header)

    assert response.status_code == 200
    assert "items" in response.json()
    assert "total" in response.json()
    assert "page" in response.json()
    assert "size" in response.json()
    assert "pages" in response.json()
    assert isinstance(response.json()["total"], int)
    assert isinstance(response.json()["page"], int)
    assert isinstance(response.json()["size"], int)
    assert response.json()["total"] == 0
    assert response.json()["page"] == 1
    assert response.json()["size"] == 100
    assert response.json()["pages"] == 0
    assert isinstance(response.json()["pages"], int)
    assert len(response.json()["items"]) == 0
