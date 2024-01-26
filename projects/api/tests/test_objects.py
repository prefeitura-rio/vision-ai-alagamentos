# -*- coding: utf-8 -*-
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
@pytest.mark.run(order=1)
async def test_objects_get(client: AsyncClient, authorization_header: dict) -> None:
    response = await client.get("/objects", headers=authorization_header)
    assert response.status_code == 200
    assert "items" in response.json()
    assert "total" in response.json()
    assert "page" in response.json()
    assert "size" in response.json()
    assert "pages" in response.json()
    assert len(response.json()["items"]) == 3
    for item in response.json()["items"]:
        assert "id" in item
        assert "name" in item
        assert "slug" in item
        assert isinstance(item["id"], str)
        assert isinstance(item["name"], str)
        assert isinstance(item["slug"], str)
    assert response.json()["total"] == 3
    assert response.json()["page"] == 1
    assert response.json()["size"] == 50
    assert response.json()["pages"] == 1


@pytest.mark.anyio
@pytest.mark.run(order=2)
async def test_objects_create(
    client: AsyncClient, authorization_header: dict, context: dict
) -> None:
    response = await client.post(
        "/objects",
        headers=authorization_header,
        json={"name": "Test Object", "slug": "test-object"},
    )
    assert response.status_code == 200
    assert "id" in response.json()
    assert "name" in response.json()
    assert "slug" in response.json()
    assert isinstance(response.json()["id"], str)
    assert isinstance(response.json()["name"], str)
    assert isinstance(response.json()["slug"], str)
    assert response.json()["name"] == "Test Object"
    assert response.json()["slug"] == "test-object"
    context["test_object_id"] = response.json()["id"]
    context["test_object_slug"] = response.json()["slug"]


@pytest.mark.anyio
@pytest.mark.run(order=999)
async def test_objects_delete(
    client: AsyncClient, authorization_header: dict, context: dict
) -> None:
    object_id = context["test_object_id"]
    response = await client.delete(
        f"/objects/{object_id}",
        headers=authorization_header,
    )
    assert response.status_code == 200
    assert "id" in response.json()
    assert "name" in response.json()
    assert "slug" in response.json()
    assert isinstance(response.json()["id"], str)
    assert isinstance(response.json()["name"], str)
    assert isinstance(response.json()["slug"], str)
