# -*- coding: utf-8 -*-
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
            assert "timestamp" in identification
            assert "label" in identification
            assert isinstance(identification["object"], str)
            assert (
                isinstance(identification["timestamp"], str) or identification["timestamp"] is None
            )
            assert isinstance(identification["label"], bool) or identification["label"] is None


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


@pytest.mark.anyio
@pytest.mark.run(order=24)
async def test_cameras_add_objects(client: AsyncClient, authorization_header: dict, context: dict):
    response = await client.post(
        f"/cameras/{context['test_camera_id']}/objects?object_id={context['test_object_id']}",
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
@pytest.mark.run(order=25)
async def test_cameras_get_objects(client: AsyncClient, authorization_header: dict, context: dict):
    response = await client.get(
        f"/cameras/{context['test_camera_id']}/objects", headers=authorization_header
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
@pytest.mark.run(order=26)
async def test_cameras_get_object_by_id(
    client: AsyncClient, authorization_header: dict, context: dict
):
    response = await client.get(
        f"/cameras/{context['test_camera_id']}/objects/{context['test_object_id']}",
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
@pytest.mark.run(order=27)
async def test_cameras_update_object(
    client: AsyncClient, authorization_header: dict, context: dict
):
    response = await client.put(
        f"/cameras/{context['test_camera_id']}/objects/{context['test_object_id']}?label=true",
        headers=authorization_header,
    )
    assert response.status_code == 200
    assert "object" in response.json()
    assert "timestamp" in response.json()
    assert "label" in response.json()
    assert isinstance(response.json()["object"], str)
    assert isinstance(response.json()["timestamp"], str)
    assert isinstance(response.json()["label"], bool)
    assert response.json()["object"] == context["test_object_slug"]
    assert response.json()["label"] is True


@pytest.mark.anyio
@pytest.mark.run(order=28)
async def test_cameras_delete_object(
    client: AsyncClient, authorization_header: dict, context: dict
):
    response = await client.delete(
        f"/cameras/{context['test_camera_id']}/objects/{context['test_object_id']}",
        headers=authorization_header,
    )
    assert response.status_code == 200


@pytest.mark.anyio
@pytest.mark.run(order=29)
async def test_cameras_post_snapshot(
    client: AsyncClient, authorization_header: dict, context: dict, image_base64: str
):
    response = await client.post(
        f"/cameras/{context['test_camera_id']}/snapshot",
        headers=authorization_header,
        json={
            "image_base64": image_base64,
        },
    )
    assert response.status_code == 200
    assert "error" in response.json()
    assert "message" in response.json()
    assert isinstance(response.json()["error"], bool)
    assert isinstance(response.json()["message"], str)
    assert response.json()["error"] is False


@pytest.mark.anyio
@pytest.mark.run(order=30)
async def test_cameras_get_snapshot(client: AsyncClient, authorization_header: dict, context: dict):
    response = await client.get(
        f"/cameras/{context['test_camera_id']}/snapshot", headers=authorization_header
    )
    assert response.status_code == 200
    assert "image_base64" in response.json()
    assert isinstance(response.json()["image_base64"], str)
    assert len(response.json()["image_base64"]) > 0
