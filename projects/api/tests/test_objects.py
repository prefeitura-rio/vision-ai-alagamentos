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
        assert "title" in item
        assert "explanation" in item
        assert "labels" in item
        assert isinstance(item["id"], str)
        assert isinstance(item["name"], str)
        assert isinstance(item["slug"], str)
        assert isinstance(item["title"], str)
        assert isinstance(item["explanation"], str)
        assert isinstance(item["labels"], list)
        assert len(item["labels"]) == 2
        for label in item["labels"]:
            assert "id" in label
            assert "value" in label
            assert "criteria" in label
            assert "text" in label
            assert "identification_guide" in label
            assert isinstance(label["id"], str)
            assert isinstance(label["value"], str)
            assert isinstance(label["criteria"], str)
            assert isinstance(label["text"], str)
            assert isinstance(label["identification_guide"], str)
    assert response.json()["total"] == 3
    assert response.json()["page"] == 1
    assert response.json()["size"] == 50
    assert response.json()["pages"] == 1


@pytest.mark.anyio
@pytest.mark.run(order=2)
async def test_objects_create(
    client: AsyncClient,
    authorization_header: dict,
    context: dict,
) -> None:
    response = await client.post(
        "/objects",
        headers=authorization_header,
        json={
            "name": "Test Object",
            "slug": "test-object",
            "title": "Tittle Test",
            "explanation": "Explaning tittle test",
        },
    )
    assert response.status_code == 200
    assert "id" in response.json()
    assert "name" in response.json()
    assert "slug" in response.json()
    assert "title" in response.json()
    assert "explanation" in response.json()
    assert isinstance(response.json()["id"], str)
    assert isinstance(response.json()["name"], str)
    assert isinstance(response.json()["slug"], str)
    assert isinstance(response.json()["title"], str)
    assert isinstance(response.json()["explanation"], str)
    assert response.json()["name"] == "Test Object"
    assert response.json()["slug"] == "test-object"
    assert response.json()["title"] == "Tittle Test"
    assert response.json()["explanation"] == "Explaning tittle test"
    context["test_object_id"] = response.json()["id"]
    context["test_object_slug"] = response.json()["slug"]
    context["test_object_title"] = response.json()["title"]
    context["test_object_explanation"] = response.json()["explanation"]


@pytest.mark.anyio
@pytest.mark.run(order=3)
async def test_object_add_labels(
    client: AsyncClient,
    authorization_header: dict,
    context: dict,
) -> None:
    object_id = context["test_object_id"]
    label_value = "test-label"
    response = await client.post(
        f"/objects/{object_id}/labels",
        headers=authorization_header,
        json={
            "value": label_value,
            "criteria": "Test Criteria",
            "identification_guide": "Test Identification Guide",
            "text": "Texto teste",
        },
    )
    assert response.status_code == 200
    assert "id" in response.json()
    assert "value" in response.json()
    assert "criteria" in response.json()
    assert "text" in response.json()
    assert "identification_guide" in response.json()
    assert isinstance(response.json()["id"], str)
    assert isinstance(response.json()["value"], str)
    assert isinstance(response.json()["criteria"], str)
    assert isinstance(response.json()["text"], str)
    assert isinstance(response.json()["identification_guide"], str)
    assert response.json()["value"] == label_value
    assert response.json()["criteria"] == "Test Criteria"
    assert response.json()["text"] == "Texto teste"
    assert response.json()["identification_guide"] == "Test Identification Guide"
    context["test_label_id"] = response.json()["id"]
    context["test_label_value"] = response.json()["value"]
    context["test_label_text"] = response.json()["text"]

    response = await client.post(
        f"/objects/{object_id}/labels",
        headers=authorization_header,
        json={
            "value": "test-label1",
            "criteria": "Test Criteria",
            "identification_guide": "Test Identification Guide",
            "text": "Texto teste",
        },
    )
    assert response.status_code == 200


@pytest.mark.anyio
@pytest.mark.run(order=4)
async def test_object_get_labels(
    client: AsyncClient,
    authorization_header: dict,
    context: dict,
) -> None:
    object_id = context["test_object_id"]
    response = await client.get(
        f"/objects/{object_id}/labels",
        headers=authorization_header,
    )
    assert response.status_code == 200
    assert "items" in response.json()
    assert "total" in response.json()
    assert "page" in response.json()
    assert "size" in response.json()
    assert "pages" in response.json()
    assert len(response.json()["items"]) == 2
    labels = []
    for item in response.json()["items"]:
        assert "id" in item
        assert "value" in item
        assert "criteria" in item
        assert "text" in item
        assert "identification_guide" in item
        assert isinstance(item["id"], str)
        assert isinstance(item["value"], str)
        assert isinstance(item["criteria"], str)
        assert isinstance(item["text"], str)
        assert isinstance(item["identification_guide"], str)
        labels.append(item["value"])
    assert labels == ["test-label", "test-label1"]
    assert response.json()["items"][0]["id"] == context["test_label_id"]
    assert response.json()["items"][0]["value"] == context["test_label_value"]
    assert response.json()["items"][0]["criteria"] == "Test Criteria"
    assert response.json()["items"][0]["text"] == "Texto teste"
    assert response.json()["items"][0]["identification_guide"] == "Test Identification Guide"
    assert response.json()["total"] == 2
    assert response.json()["page"] == 1
    assert response.json()["size"] == 50
    assert response.json()["pages"] == 1


@pytest.mark.anyio
@pytest.mark.run(order=5)
async def test_object_update_label_by_value(
    client: AsyncClient,
    authorization_header: dict,
    context: dict,
) -> None:
    object_id = context["test_object_id"]
    label_value = context["test_label_value"]
    response = await client.put(
        f"/objects/{object_id}/labels/{label_value}",
        headers=authorization_header,
        json={
            "value": "test-label3",
            "criteria": "Test Criteria3",
            "text": "Texto 3",
            "identification_guide": "Test Identification Guide3",
        },
    )
    assert response.status_code == 200
    assert "id" in response.json()
    assert "value" in response.json()
    assert "criteria" in response.json()
    assert "text" in response.json()
    assert "identification_guide" in response.json()
    assert isinstance(response.json()["id"], str)
    assert isinstance(response.json()["value"], str)
    assert isinstance(response.json()["criteria"], str)
    assert isinstance(response.json()["text"], str)
    assert isinstance(response.json()["identification_guide"], str)
    assert response.json()["id"] == context["test_label_id"]
    assert response.json()["value"] == "test-label3"
    assert response.json()["criteria"] == "Test Criteria3"
    assert response.json()["text"] == "Texto 3"
    assert response.json()["identification_guide"] == "Test Identification Guide3"
    context["test_label_value"] = response.json()["value"]


@pytest.mark.anyio
@pytest.mark.run(order=6)
async def test_object_update_label_by_id(
    client: AsyncClient,
    authorization_header: dict,
    context: dict,
) -> None:
    object_id = context["test_object_id"]
    label_id = context["test_label_id"]
    response = await client.put(
        f"/objects/{object_id}/labels/{label_id}",
        headers=authorization_header,
        json={
            "value": "test-label2",
            "criteria": "Test Criteria2",
            "identification_guide": "Test Identification Guide2",
            "text": "Texto 2",
        },
    )
    assert response.status_code == 200
    assert "id" in response.json()
    assert "value" in response.json()
    assert "criteria" in response.json()
    assert "text" in response.json()
    assert "identification_guide" in response.json()
    assert isinstance(response.json()["id"], str)
    assert isinstance(response.json()["value"], str)
    assert isinstance(response.json()["criteria"], str)
    assert isinstance(response.json()["text"], str)
    assert isinstance(response.json()["identification_guide"], str)
    assert response.json()["id"] == context["test_label_id"]
    assert response.json()["value"] == "test-label2"
    assert response.json()["criteria"] == "Test Criteria2"
    assert response.json()["text"] == "Texto 2"
    assert response.json()["identification_guide"] == "Test Identification Guide2"
    context["test_label_value"] = response.json()["value"]
    context["test_label_text"] = response.json()["text"]


@pytest.mark.anyio
@pytest.mark.run(order=8)
async def test_object_label_order(
    client: AsyncClient,
    authorization_header: dict,
    context: dict,
) -> None:
    object_id = context["test_object_id"]
    response = await client.post(
        f"/objects/{object_id}/labels/order",
        headers=authorization_header,
        json={
            "labels": ["test-label1", "test-label2"],
        },
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    labels = []
    for item in response.json():
        assert "id" in item
        assert "value" in item
        assert "criteria" in item
        assert "text" in item
        assert "identification_guide" in item
        assert isinstance(item["id"], str)
        assert isinstance(item["value"], str)
        assert isinstance(item["criteria"], str)
        assert isinstance(item["text"], str)
        assert isinstance(item["identification_guide"], str)
        labels.append(item["value"])
    assert labels == ["test-label1", "test-label2"]


@pytest.mark.anyio
@pytest.mark.run(order=999)
async def test_object_delete_label_by_id(
    client: AsyncClient,
    authorization_header: dict,
    context: dict,
) -> None:
    object_id = context["test_object_id"]
    label_id = context["test_label_id"]
    response = await client.delete(
        f"/objects/{object_id}/labels/{label_id}",
        headers=authorization_header,
    )
    assert response.status_code == 200
    assert "id" in response.json()
    assert "value" in response.json()
    assert "criteria" in response.json()
    assert "text" in response.json()
    assert "identification_guide" in response.json()
    assert isinstance(response.json()["id"], str)
    assert isinstance(response.json()["value"], str)
    assert isinstance(response.json()["criteria"], str)
    assert isinstance(response.json()["text"], str)
    assert isinstance(response.json()["identification_guide"], str)


@pytest.mark.anyio
@pytest.mark.run(order=1000)
async def test_objects_delete(
    client: AsyncClient,
    authorization_header: dict,
    context: dict,
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
    assert "title" in response.json()
    assert "explanation" in response.json()
    assert isinstance(response.json()["id"], str)
    assert isinstance(response.json()["name"], str)
    assert isinstance(response.json()["slug"], str)
    assert isinstance(response.json()["title"], str)
    assert isinstance(response.json()["explanation"], str)
