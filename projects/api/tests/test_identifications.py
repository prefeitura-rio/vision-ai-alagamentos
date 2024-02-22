# -*- coding: utf-8 -*-
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
@pytest.mark.run(order=51)
async def test_get_all_ai_identification(
    client: AsyncClient,
    authorization_header: dict,
    context: dict,
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
    assert response.json()["total"] == 7
    assert response.json()["page"] == 1
    assert response.json()["size"] == 50
    assert response.json()["pages"] == 1
    assert isinstance(response.json()["pages"], int)
    assert len(response.json()["items"]) == 7
    for item in response.json()["items"]:
        assert "id" in item
        assert "object" in item
        assert "title" in item
        assert "explanation" in item
        assert "timestamp" in item
        assert "label" in item
        assert "possible_labels" in item
        assert "ai_explanation" in item
        assert "snapshot_url" in item
        assert isinstance(item["id"], str)
        assert isinstance(item["object"], str)
        assert isinstance(item["title"], str)
        assert isinstance(item["explanation"], str)
        assert isinstance(item["timestamp"], str)
        assert isinstance(item["label"], str)
        assert isinstance(item["possible_labels"], list)
        assert len(item["possible_labels"]) == 2
        if item["id"] == context["test_identification_id"]:
            assert item["possible_labels"] == ["test-label1", "test-label2"]
        else:
            assert item["possible_labels"] == ["found", "not-found"]
        assert isinstance(item["ai_explanation"], str)
        assert isinstance(item["snapshot_url"], str)


@pytest.mark.anyio
@pytest.mark.run(order=52)
async def test_create_human_identification(
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
@pytest.mark.run(order=53)
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
    assert response.json()["total"] == 6
    assert response.json()["page"] == 1
    assert response.json()["size"] == 50
    assert response.json()["pages"] == 1
    assert isinstance(response.json()["pages"], int)
    assert len(response.json()["items"]) == 6
    for item in response.json()["items"]:
        assert "id" in item
        assert "object" in item
        assert "title" in item
        assert "explanation" in item
        assert "timestamp" in item
        assert "label" in item
        assert "possible_labels" in item
        assert "ai_explanation" in item
        assert "snapshot_url" in item
        assert isinstance(item["id"], str)
        assert isinstance(item["object"], str)
        assert isinstance(item["title"], str)
        assert isinstance(item["explanation"], str)
        assert isinstance(item["timestamp"], str)
        assert isinstance(item["label"], str)
        assert isinstance(item["possible_labels"], list)
        assert len(item["possible_labels"]) == 2
        assert item["possible_labels"] == ["found", "not-found"]
        assert isinstance(item["ai_explanation"], str)
        assert isinstance(item["snapshot_url"], str)
