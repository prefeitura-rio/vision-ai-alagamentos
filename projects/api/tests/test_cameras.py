# -*- coding: utf-8 -*-
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
@pytest.mark.run(order=41)
async def test_cameras_get(client: AsyncClient, authorization_header: dict):
    response = await client.get("/cameras", headers=authorization_header)
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
        assert "rtsp_url" in item
        assert "update_interval" in item
        assert "latitude" in item
        assert "longitude" in item
        assert "objects" in item
        assert "identifications" in item
        assert isinstance(item["id"], str)
        assert isinstance(item["name"], str)
        assert isinstance(item["rtsp_url"], str)
        assert isinstance(item["update_interval"], int)
        assert isinstance(item["latitude"], float)
        assert isinstance(item["longitude"], float)
        assert isinstance(item["objects"], list)
        for object_ in item["objects"]:
            assert isinstance(object_, str)
        assert isinstance(item["identifications"], list)
        for identification in item["identifications"]:
            assert "object" in identification
            assert "title" in identification
            assert "question" in identification
            assert "explanation" in identification
            assert "timestamp" in identification
            assert "label" in identification
            assert "label_text" in identification
            assert "label_explanation" in identification
            assert "snapshot" in identification
            assert "id" in identification["snapshot"]
            assert "camera_id" in identification["snapshot"]
            assert "image_url" in identification["snapshot"]
            assert "timestamp" in identification["snapshot"]
            assert isinstance(identification["object"], str)
            assert isinstance(identification["title"], str)
            assert isinstance(identification["question"], str)
            assert isinstance(identification["explanation"], str)
            assert isinstance(identification["timestamp"], str)
            assert isinstance(identification["label"], str)
            assert isinstance(identification["label_text"], str)
            assert isinstance(identification["label_explanation"], str)
            assert isinstance(identification["snapshot"], dict)
            assert isinstance(identification["snapshot"]["id"], str)
            assert isinstance(identification["snapshot"]["camera_id"], str)
            assert isinstance(identification["snapshot"]["image_url"], str)
            assert isinstance(identification["snapshot"]["timestamp"], str)


@pytest.mark.anyio
@pytest.mark.run(order=42)
async def test_cameras_create(client: AsyncClient, authorization_header: dict, context: dict):
    response = await client.post(
        "/cameras",
        headers=authorization_header,
        json={
            "id": "0004",
            "name": "Camera 4",
            "rtsp_url": "rtsp://four",
            "update_interval": 30,
            "latitude": 4.0,
            "longitude": 4.0,
        },
    )
    assert response.status_code == 200
    assert "id" in response.json()
    assert "name" in response.json()
    assert "rtsp_url" in response.json()
    assert "update_interval" in response.json()
    assert "latitude" in response.json()
    assert "longitude" in response.json()
    assert isinstance(response.json()["id"], str)
    assert isinstance(response.json()["name"], str)
    assert isinstance(response.json()["rtsp_url"], str)
    assert isinstance(response.json()["update_interval"], int)
    assert isinstance(response.json()["latitude"], float)
    assert isinstance(response.json()["longitude"], float)
    context["test_camera_id"] = response.json()["id"]


@pytest.mark.anyio
@pytest.mark.run(order=43)
async def test_cameras_get_by_id(client: AsyncClient, authorization_header: dict, context: dict):
    response = await client.get(
        f"/cameras/{context['test_camera_id']}", headers=authorization_header
    )
    assert response.status_code == 200
    assert "id" in response.json()
    assert "name" in response.json()
    assert "rtsp_url" in response.json()
    assert "update_interval" in response.json()
    assert "latitude" in response.json()
    assert "longitude" in response.json()
    assert isinstance(response.json()["id"], str)
    assert isinstance(response.json()["name"], str)
    assert isinstance(response.json()["rtsp_url"], str)
    assert isinstance(response.json()["update_interval"], int)
    assert isinstance(response.json()["latitude"], float)
    assert isinstance(response.json()["longitude"], float)
    assert response.json()["id"] == context["test_camera_id"]


@pytest.mark.anyio
@pytest.mark.run(order=43)
async def test_agents_add_cameras(client: AsyncClient, authorization_header: dict, context: dict):
    response = await client.post(
        f"/agents/{context['agent_id']}/cameras/{context['test_camera_id']}",
        headers=authorization_header,
    )
    assert response.status_code == 200
    assert "id" in response.json()
    assert "rtsp_url" in response.json()
    assert "update_interval" in response.json()
    assert isinstance(response.json()["id"], str)
    assert isinstance(response.json()["rtsp_url"], str)
    assert isinstance(response.json()["update_interval"], int)
    assert response.json()["id"] == context["test_camera_id"]


@pytest.mark.anyio
@pytest.mark.run(order=44)
async def test_snapshot_create(client: AsyncClient, authorization_header: dict, context: dict):
    response = await client.post(
        f"/cameras/{context['test_camera_id']}/snapshots",
        headers=authorization_header,
        json={
            "hash_md5": "MWNhMzA4ZGY2Y2RiMGE4YmY0MGQ1OWJlMmExN2VhYzEK",
            "content_length": 1234,
        },
    )
    assert response.status_code == 200
    assert "id" in response.json()
    assert "camera_id" in response.json()
    assert "image_url" in response.json()
    assert "timestamp" in response.json()
    assert isinstance(response.json()["id"], str)
    assert isinstance(response.json()["camera_id"], str)
    assert isinstance(response.json()["image_url"], str)
    assert response.json()["timestamp"] is None
    assert context["test_camera_id"] == response.json()["camera_id"]
    context["test_snapshot_id"] = response.json()["id"]


@pytest.mark.anyio
@pytest.mark.run(order=45)
async def test_snapshots_get(client: AsyncClient, authorization_header: dict, context: dict):
    response = await client.get(
        f"/cameras/{context['test_camera_id']}/snapshots", headers=authorization_header
    )
    assert response.status_code == 200
    assert "items" in response.json()
    assert "total" in response.json()
    assert "page" in response.json()
    assert "size" in response.json()
    assert "pages" in response.json()
    assert len(response.json()["items"]) == 1
    for item in response.json()["items"]:
        assert "id" in item
        assert "camera_id" in item
        assert "image_url" in item
        assert "timestamp" in item
        assert isinstance(item["id"], str)
        assert isinstance(item["camera_id"], str)
        assert isinstance(item["image_url"], str)
        assert item["timestamp"] is None


@pytest.mark.anyio
@pytest.mark.run(order=46)
async def test_add_object_to_camera(client: AsyncClient, authorization_header: dict, context: dict):
    path = f"/objects/{context['test_object_id']}/cameras/{context['test_camera_id']}"
    response = await client.post(f"{path}", headers=authorization_header)

    assert response.status_code == 200
    assert "id" in response.json()
    assert "name" in response.json()
    assert "rtsp_url" in response.json()
    assert "update_interval" in response.json()
    assert "latitude" in response.json()
    assert "longitude" in response.json()
    assert isinstance(response.json()["id"], str)
    assert isinstance(response.json()["name"], str)
    assert isinstance(response.json()["rtsp_url"], str)
    assert isinstance(response.json()["update_interval"], int)
    assert isinstance(response.json()["latitude"], float)
    assert isinstance(response.json()["longitude"], float)
    assert response.json()["id"] == context["test_camera_id"]


@pytest.mark.anyio
@pytest.mark.run(order=47)
async def test_snapshot_predict(client: AsyncClient, authorization_header: dict, context: dict):
    path = f"/cameras/{context['test_camera_id']}/snapshots/{context['test_snapshot_id']}/predict"
    response = await client.post(path, headers=authorization_header)

    assert response.status_code == 200
    assert "error" in response.json()
    assert "message" in response.json()
    assert isinstance(response.json()["error"], bool)
    assert isinstance(response.json()["message"], str)
    assert response.json()["error"] is False


@pytest.mark.anyio
@pytest.mark.run(order=48)
async def test_create_identification(
    client: AsyncClient,
    authorization_header: dict,
    context: dict,
):
    path = f"/cameras/{context['test_camera_id']}/snapshots/{context['test_snapshot_id']}/identifications"  # noqa
    paramaters = f"object_id={context['test_object_id']}&label_value={context['test_label_value']}&label_explanation=test"  # noqa
    response = await client.post(f"{path}?{paramaters}", headers=authorization_header)

    assert response.status_code == 200
    assert "id" in response.json()
    assert "object" in response.json()
    assert "title" in response.json()
    assert "question" in response.json()
    assert "explanation" in response.json()
    assert "timestamp" in response.json()
    assert "label" in response.json()
    assert "label_text" in response.json()
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
    assert isinstance(response.json()["label_text"], str)
    assert isinstance(response.json()["label_explanation"], str)
    assert isinstance(response.json()["snapshot"]["id"], str)
    assert isinstance(response.json()["snapshot"]["camera_id"], str)
    assert isinstance(response.json()["snapshot"]["image_url"], str)
    assert isinstance(response.json()["snapshot"]["timestamp"], str)
    assert response.json()["object"] == context["test_object_slug"]
    assert response.json()["label"] == context["test_label_value"]
    assert response.json()["label_text"] == context["test_label_text"]
    assert response.json()["snapshot"]["id"] == context["test_snapshot_id"]
    context["test_identification_id"] = response.json()["id"]


@pytest.mark.anyio
@pytest.mark.run(order=49)
async def test_get_identifications(client: AsyncClient, authorization_header: dict, context: dict):
    path = f"/cameras/{context['test_camera_id']}/snapshots/{context['test_snapshot_id']}/identifications"  # noqa
    response = await client.get(path, headers=authorization_header)

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    for item in response.json():
        assert "id" in item
        assert "object" in item
        assert "title" in item
        assert "question" in item
        assert "explanation" in item
        assert "timestamp" in item
        assert "label" in item
        assert "label_text" in item
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
        assert isinstance(item["label_text"], str)
        assert isinstance(item["label_explanation"], str)
        assert isinstance(item["snapshot"]["id"], str)
        assert isinstance(item["snapshot"]["camera_id"], str)
        assert isinstance(item["snapshot"]["image_url"], str)
        assert isinstance(item["snapshot"]["timestamp"], str)
    assert response.json()[0]["id"] == context["test_identification_id"]
    assert response.json()[0]["object"] == context["test_object_slug"]
    assert response.json()[0]["label"] == context["test_label_value"]
    assert response.json()[0]["label_text"] == context["test_label_text"]
    assert response.json()[0]["snapshot"]["id"] == context["test_snapshot_id"]


@pytest.mark.anyio
@pytest.mark.run(order=60)
async def test_delete_identifications(
    client: AsyncClient,
    authorization_header: dict,
    context: dict,
):
    path = f"/cameras/{context['test_camera_id']}/snapshots/{context['test_snapshot_id']}/identifications/{context['test_identification_id']}"  # noqa
    response = await client.delete(path, headers=authorization_header)
    assert response.status_code == 200


@pytest.mark.anyio
@pytest.mark.run(order=61)
async def test_delete_camera(client: AsyncClient, authorization_header: dict, context: dict):
    path = f"/cameras/{context['test_camera_id']}"
    response = await client.delete(path, headers=authorization_header)
    assert response.status_code == 200
