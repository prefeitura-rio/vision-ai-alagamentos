# -*- coding: utf-8 -*-
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
@pytest.mark.run(order=31)
async def test_agents_get(client: AsyncClient, authorization_header: dict, context: dict):
    response = await client.get("/agents", headers=authorization_header)
    assert response.status_code == 200
    assert "items" in response.json()
    assert "total" in response.json()
    assert "page" in response.json()
    assert "size" in response.json()
    assert "pages" in response.json()
    assert isinstance(response.json()["items"], list)
    for item in response.json()["items"]:
        assert "id" in item
        assert "name" in item
        assert "slug" in item
        assert "auth_sub" in item
        assert "last_heartbeat" in item
        assert isinstance(item["id"], str)
        assert isinstance(item["name"], str)
        assert isinstance(item["slug"], str)
        assert isinstance(item["auth_sub"], str)
        assert isinstance(item["last_heartbeat"], str) or item["last_heartbeat"] is None
    assert isinstance(response.json()["total"], int)
    assert isinstance(response.json()["page"], int)
    assert isinstance(response.json()["size"], int)
    assert isinstance(response.json()["pages"], int)
    context["agent_id"] = response.json()["items"][0]["id"]


@pytest.mark.anyio
@pytest.mark.run(order=32)
async def test_agents_me_get(client: AsyncClient, authorization_header: dict, context: dict):
    response = await client.get("/agents/me", headers=authorization_header)
    assert response.status_code == 200
    assert "id" in response.json()
    assert "name" in response.json()
    assert "slug" in response.json()
    assert "auth_sub" in response.json()
    assert "last_heartbeat" in response.json()
    assert isinstance(response.json()["id"], str)
    assert isinstance(response.json()["name"], str)
    assert isinstance(response.json()["slug"], str)
    assert isinstance(response.json()["auth_sub"], str)
    assert (
        isinstance(response.json()["last_heartbeat"], str)
        or response.json()["last_heartbeat"] is None
    )
    context["agent_id"] = response.json()["id"]


@pytest.mark.anyio
@pytest.mark.run(order=33)
async def test_agents_get_cameras(client: AsyncClient, authorization_header: dict):
    response = await client.get("/agents/cameras", headers=authorization_header)
    assert response.status_code == 200
    assert "items" in response.json()
    assert "total" in response.json()
    assert "page" in response.json()
    assert "size" in response.json()
    assert "pages" in response.json()
    assert isinstance(response.json()["items"], list)
    for item in response.json()["items"]:
        assert "id" in item
        assert "rtsp_url" in item
        assert "update_interval" in item
    assert isinstance(response.json()["total"], int)
    assert isinstance(response.json()["page"], int)
    assert isinstance(response.json()["size"], int)
    assert isinstance(response.json()["pages"], int)


@pytest.mark.anyio
@pytest.mark.run(order=34)
async def test_agents_add_cameras(client: AsyncClient, authorization_header: dict, context: dict):
    response = await client.post(
        f"/agents/{context['agent_id']}/cameras?camera_id=0001",
        headers=authorization_header,
    )
    assert response.status_code == 200
    assert "id" in response.json()
    assert "rtsp_url" in response.json()
    assert "update_interval" in response.json()
    assert isinstance(response.json()["id"], str)
    assert isinstance(response.json()["rtsp_url"], str)
    assert isinstance(response.json()["update_interval"], int)
    assert response.json()["id"] == "0001"


@pytest.mark.anyio
@pytest.mark.run(order=35)
async def test_agents_get_by_id_cameras(
    client: AsyncClient, authorization_header: dict, context: dict
):
    response = await client.get(
        f"/agents/{context['agent_id']}/cameras", headers=authorization_header
    )
    assert response.status_code == 200
    assert "items" in response.json()
    assert "total" in response.json()
    assert "page" in response.json()
    assert "size" in response.json()
    assert "pages" in response.json()
    assert isinstance(response.json()["items"], list)
    for item in response.json()["items"]:
        assert "id" in item
        assert "rtsp_url" in item
        assert "update_interval" in item
    assert isinstance(response.json()["total"], int)
    assert isinstance(response.json()["page"], int)
    assert isinstance(response.json()["size"], int)
    assert isinstance(response.json()["pages"], int)


@pytest.mark.anyio
@pytest.mark.run(order=36)
async def test_agents_post_heartbeat_to_other(
    client: AsyncClient, authorization_header: dict, context: dict
):
    response = await client.post(
        f"/agents/{context['agent_id']}/heartbeat",
        headers=authorization_header,
        json={"healthy": True},
    )
    assert response.status_code == 401
