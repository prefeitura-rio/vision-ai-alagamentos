# -*- coding: utf-8 -*-
import base64
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
@pytest.mark.run(order=21)
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
            assert "explanation" in identification
            assert "timestamp" in identification
            assert "label" in identification
            assert "label_explanation" in identification
            assert "snapshot" in identification
            assert "id" in identification["snapshot"]
            assert "camera_id" in identification["snapshot"]
            assert "image_url" in identification["snapshot"]
            assert "timestamp" in identification["snapshot"]
            assert isinstance(identification["object"], str)
            assert isinstance(identification["title"], str)
            assert isinstance(identification["explanation"], str)
            assert isinstance(identification["timestamp"], str)
            assert isinstance(identification["label"], str)
            assert isinstance(identification["label_explanation"], str)
            assert isinstance(identification["snapshot"], dict)
            assert isinstance(identification["snapshot"]["id"], str)
            assert isinstance(identification["snapshot"]["camera_id"], str)
            assert isinstance(identification["snapshot"]["image_url"], str)
            assert isinstance(identification["snapshot"]["timestamp"], str)


@pytest.mark.anyio
@pytest.mark.run(order=22)
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
@pytest.mark.run(order=23)
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
    assert response.json()["id"] == context["test_camera_id"]


@pytest.mark.anyio
@pytest.mark.run(order=23)
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
@pytest.mark.run(order=24)
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


@pytest.mark.anyio
@pytest.mark.run(order=25)
async def test_snapshots_get(client: AsyncClient, authorization_header: dict, context: dict):
    response = await client.get(
        f"/cameras/{context['test_camera_id']}/snapshots", headers=authorization_header
    )
    print(response.json())
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
@pytest.mark.run(order=26)
async def test_add_identification(client: AsyncClient, authorization_header: dict, context: dict):
    path = f"/cameras/{context['test_camera_id']}/snapshots/identifications"
    response = await client.post(
        f"{path}?identification_id={context['test_object_id']}",
        headers=authorization_header,
    )
    assert response.status_code == 200
    assert "id" in response.json()
    assert "name" in response.json()
    assert "rtsp_url" in response.json()
    assert "update_interval" in response.json()
    assert "latitude" in response.json()
    assert "longitude" in response.json()
    assert "objects" in response.json()
    assert "identifications" in response.json()
    assert isinstance(response.json()["id"], str)
    assert isinstance(response.json()["name"], str)
    assert isinstance(response.json()["rtsp_url"], str)
    assert isinstance(response.json()["update_interval"], int)
    assert isinstance(response.json()["latitude"], float)
    assert isinstance(response.json()["longitude"], float)
    assert isinstance(response.json()["objects"], list)
    for object_ in response.json()["objects"]:
        assert isinstance(object_, str)
    assert isinstance(response.json()["identifications"], list)
    for identification in response.json()["identifications"]:
        assert "object" in identification
        assert "timestamp" in identification
        assert "label" in identification
        assert isinstance(identification["object"], str)
        assert isinstance(identification["timestamp"], str) or identification["timestamp"] is None
        assert isinstance(identification["label"], bool) or identification["label"] is None
    assert response.json()["id"] == context["test_camera_id"]
    assert response.json()["objects"] == [context["test_object_slug"]]


@pytest.mark.anyio
@pytest.mark.run(order=27)
async def test_get_identifications(client: AsyncClient, authorization_header: dict, context: dict):
    response = await client.get(
        f"/cameras/{context['test_camera_id']}/snapshots/identifications",
        headers=authorization_header,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    for object_ in response.json():
        assert "object" in object_
        assert "timestamp" in object_
        assert "label" in object_
        assert isinstance(object_["object"], str)
        assert isinstance(object_["timestamp"], str) or object_["timestamp"] is None
        assert isinstance(object_["label"], bool) or object_["label"] is None


@pytest.mark.anyio
@pytest.mark.run(order=28)
async def test_get_identification_by_id(
    client: AsyncClient, authorization_header: dict, context: dict
):
    path = f"/cameras/{context['test_camera_id']}/snapshots/identifications"
    response = await client.get(
        f"{path}/{context['test_object_id']}",
        headers=authorization_header,
    )
    assert response.status_code == 200
    assert "object" in response.json()
    assert "timestamp" in response.json()
    assert "label" in response.json()
    assert isinstance(response.json()["object"], str)
    assert isinstance(response.json()["timestamp"], str) or response.json()["timestamp"] is None
    assert isinstance(response.json()["label"], bool) or response.json()["label"] is None
    assert response.json()["object"] == context["test_object_slug"]


@pytest.mark.anyio
@pytest.mark.run(order=29)
async def test_update_identification(
    client: AsyncClient, authorization_header: dict, context: dict
):
    response = await client.put(
        f"/cameras/{context['test_camera_id']}/snapshots/identifications/{context['test_object_id']}?label={context['test_label_value']}&label_explanation=something",  # noqa
        headers=authorization_header,
    )
    assert response.status_code == 200
    assert "object" in response.json()
    assert "timestamp" in response.json()
    assert "label" in response.json()
    assert "label_explanation" in response.json()
    assert isinstance(response.json()["object"], str)
    assert isinstance(response.json()["timestamp"], str)
    assert isinstance(response.json()["label"], str)
    assert isinstance(response.json()["label_explanation"], str)
    assert response.json()["object"] == context["test_object_slug"]
    assert response.json()["label"] == context["test_label_value"]


@pytest.mark.anyio
@pytest.mark.run(order=30)
async def test_delete_identification(
    client: AsyncClient, authorization_header: dict, context: dict
):
    path = f"/cameras/{context['test_camera_id']}/snapshots/identifications"
    response = await client.delete(
        f"{path}/{context['test_object_id']}",
        headers=authorization_header,
    )
    assert response.status_code == 200


@pytest.mark.anyio
@pytest.mark.run(order=31)
async def test_post_predict(
    client: AsyncClient, authorization_header: dict, context: dict, image_base64: str
):
    response = await client.post(
        f"/cameras/{context['test_camera_id']}/snapshots/identifications/predict",
        headers=authorization_header,
        files={
            "file": base64.b64decode(image_base64),
        },
        json={
            "image_base66": image_base64,
        },
    )
    assert response.status_code == 200
    assert "error" in response.json()
    assert "message" in response.json()
    assert isinstance(response.json()["error"], bool)
    assert isinstance(response.json()["message"], str)
    assert response.json()["error"] is False


@pytest.mark.anyio
@pytest.mark.run(order=32)
async def test_get_snapshot(client: AsyncClient, authorization_header: dict, context: dict):
    response = await client.get(
        f"/cameras/{context['test_camera_id']}/snapshots", headers=authorization_header
    )
    assert response.status_code == 200
    assert "image_url" in response.json()
    assert "timestamp" in response.json()
    assert isinstance(response.json()["image_url"], str)
    assert isinstance(response.json()["timestamp"], str)


@pytest.mark.anyio
@pytest.mark.run(order=33)
async def test_cameras_latest_snapshots(
    client: AsyncClient, authorization_header: dict, context: dict
):
    response = await client.get(
        f"/cameras/latest_snapshots?after={(datetime.utcnow() - timedelta(minutes=10)).isoformat()}",  # noqa
        headers=authorization_header,
    )
    assert response.status_code == 200
    assert "items" in response.json()
    assert "total" in response.json()
    assert "page" in response.json()
    assert "size" in response.json()
    assert "pages" in response.json()
    assert len(response.json()["items"]) == 1
    for item in response.json()["items"]:
        assert "image_url" in item
        assert "timestamp" in item
        assert isinstance(item["image_url"], str)
        assert isinstance(item["timestamp"], str)
