# -*- coding: utf-8 -*-
import pytest
from httpx import AsyncClient


@pytest.mark.anyio
@pytest.mark.run(order=11)
async def test_prompts_get(client: AsyncClient, authorization_header: dict) -> None:
    response = await client.get("/prompts", headers=authorization_header)
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
        assert "prompt_text" in item
        assert "max_output_token" in item
        assert "temperature" in item
        assert "top_k" in item
        assert "top_p" in item
        assert "objects" in item
        assert isinstance(item["id"], str)
        assert isinstance(item["name"], str)
        assert isinstance(item["prompt_text"], str)
        assert isinstance(item["max_output_token"], int)
        assert isinstance(item["temperature"], float)
        assert isinstance(item["top_k"], int)
        assert isinstance(item["top_p"], float)
        assert isinstance(item["objects"], list)
        for obj in item["objects"]:
            assert isinstance(obj, str)
        assert isinstance(item["objects"][0], str)
    assert response.json()["total"] == 3
    assert response.json()["page"] == 1
    assert response.json()["size"] == 50
    assert response.json()["pages"] == 1


@pytest.mark.anyio
@pytest.mark.run(order=12)
async def test_prompts_create(
    client: AsyncClient,
    authorization_header: dict,
    context: dict,
) -> None:
    response = await client.post(
        "/prompts",
        headers=authorization_header,
        json={
            "name": "Test Prompt",
            "model": "dalle-mini",
            "prompt_text": "Test Prompt Text",
            "max_output_token": 32,
            "temperature": 0.5,
            "top_k": 0,
            "top_p": 0.9,
        },
    )
    assert response.status_code == 200
    assert "id" in response.json()
    assert "name" in response.json()
    assert "model" in response.json()
    assert "prompt_text" in response.json()
    assert "max_output_token" in response.json()
    assert "temperature" in response.json()
    assert "top_k" in response.json()
    assert "top_p" in response.json()
    assert "objects" in response.json()
    assert isinstance(response.json()["id"], str)
    assert isinstance(response.json()["name"], str)
    assert isinstance(response.json()["model"], str)
    assert isinstance(response.json()["prompt_text"], str)
    assert isinstance(response.json()["max_output_token"], int)
    assert isinstance(response.json()["temperature"], float)
    assert isinstance(response.json()["top_k"], int)
    assert isinstance(response.json()["top_p"], float)
    assert isinstance(response.json()["objects"], list)
    for obj in response.json()["objects"]:
        assert isinstance(obj, str)
    assert response.json()["name"] == "Test Prompt"
    assert response.json()["model"] == "dalle-mini"
    assert response.json()["prompt_text"] == "Test Prompt Text"
    assert response.json()["max_output_token"] == 32
    assert response.json()["temperature"] == 0.5
    assert response.json()["top_k"] == 0
    assert response.json()["top_p"] == 0.9
    context["test_prompt_id"] = response.json()["id"]


@pytest.mark.anyio
@pytest.mark.run(order=13)
async def test_prompts_get_by_id(
    client: AsyncClient,
    authorization_header: dict,
    context: dict,
) -> None:
    response = await client.get(
        f"/prompts/{context['test_prompt_id']}", headers=authorization_header
    )
    assert response.status_code == 200
    assert "id" in response.json()
    assert "name" in response.json()
    assert "prompt_text" in response.json()
    assert "max_output_token" in response.json()
    assert "temperature" in response.json()
    assert "top_k" in response.json()
    assert "top_p" in response.json()
    assert "objects" in response.json()
    assert isinstance(response.json()["id"], str)
    assert isinstance(response.json()["name"], str)
    assert isinstance(response.json()["prompt_text"], str)
    assert isinstance(response.json()["max_output_token"], int)
    assert isinstance(response.json()["temperature"], float)
    assert isinstance(response.json()["top_k"], int)
    assert isinstance(response.json()["top_p"], float)
    assert isinstance(response.json()["objects"], list)
    for obj in response.json()["objects"]:
        assert isinstance(obj, str)
    assert response.json()["name"] == "Test Prompt"
    assert response.json()["prompt_text"] == "Test Prompt Text"
    assert response.json()["max_output_token"] == 32
    assert response.json()["temperature"] == 0.5
    assert response.json()["top_k"] == 0
    assert response.json()["top_p"] == 0.9


@pytest.mark.anyio
@pytest.mark.run(order=14)
async def test_prompts_update(
    client: AsyncClient,
    authorization_header: dict,
    context: dict,
) -> None:
    response = await client.put(
        f"/prompts/{context['test_prompt_id']}",
        headers=authorization_header,
        json={
            "name": "Test Prompt Updated",
            "model": "dalle-mini",
            "prompt_text": "Test Prompt Text Updated",
            "max_output_token": 64,
            "temperature": 0.75,
            "top_k": 0,
            "top_p": 0.9,
        },
    )
    assert response.status_code == 200
    assert "id" in response.json()
    assert "name" in response.json()
    assert "prompt_text" in response.json()
    assert "max_output_token" in response.json()
    assert "temperature" in response.json()
    assert "top_k" in response.json()
    assert "top_p" in response.json()
    assert "objects" in response.json()
    assert isinstance(response.json()["id"], str)
    assert isinstance(response.json()["name"], str)
    assert isinstance(response.json()["prompt_text"], str)
    assert isinstance(response.json()["max_output_token"], int)
    assert isinstance(response.json()["temperature"], float)
    assert isinstance(response.json()["top_k"], int)
    assert isinstance(response.json()["top_p"], float)
    assert isinstance(response.json()["objects"], list)
    for obj in response.json()["objects"]:
        assert isinstance(obj, str)
    assert response.json()["name"] == "Test Prompt Updated"
    assert response.json()["prompt_text"] == "Test Prompt Text Updated"
    assert response.json()["max_output_token"] == 64
    assert response.json()["temperature"] == 0.75
    assert response.json()["top_k"] == 0
    assert response.json()["top_p"] == 0.9


@pytest.mark.anyio
@pytest.mark.run(order=15)
async def test_prompts_add_objects(
    client: AsyncClient,
    authorization_header: dict,
    context: dict,
) -> None:
    response = await client.post(
        f"/prompts/{context['test_prompt_id']}/objects?object_id={context['test_object_id']}",
        headers=authorization_header,
    )
    assert response.status_code == 200
    assert "id" in response.json()
    assert "name" in response.json()
    assert "slug" in response.json()
    assert "title" in response.json()
    assert "explanation" in response.json()
    assert response.json()["id"] == context["test_object_id"]
    assert response.json()["slug"] == context["test_object_slug"]
    assert response.json()["title"] == context["test_object_title"]
    assert response.json()["explanation"] == context["test_object_explanation"]


@pytest.mark.anyio
@pytest.mark.run(order=16)
async def test_prompts_get_objects(
    client: AsyncClient,
    authorization_header: dict,
    context: dict,
) -> None:
    response = await client.get(
        f"/prompts/{context['test_prompt_id']}/objects", headers=authorization_header
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1
    assert "id" in response.json()[0]
    assert "name" in response.json()[0]
    assert "slug" in response.json()[0]
    assert "title" in response.json()[0]
    assert "explanation" in response.json()[0]
    assert response.json()[0]["id"] == context["test_object_id"]
    assert response.json()[0]["slug"] == context["test_object_slug"]
    assert response.json()[0]["title"] == context["test_object_title"]
    assert response.json()[0]["explanation"] == context["test_object_explanation"]


@pytest.mark.anyio
@pytest.mark.run(order=17)
async def test_prompts_best_fit(client: AsyncClient, authorization_header: dict) -> None:
    response = await client.post(
        "/prompts/best_fit",
        headers=authorization_header,
        json={"objects": ["person", "car"]},
    )
    assert response.status_code == 200
    assert "prompts" in response.json()
    assert isinstance(response.json()["prompts"], list)
    assert len(response.json()["prompts"]) == 1
    assert "id" in response.json()["prompts"][0]
    assert "name" in response.json()["prompts"][0]
    assert "prompt_text" in response.json()["prompts"][0]
    assert "max_output_token" in response.json()["prompts"][0]
    assert "temperature" in response.json()["prompts"][0]
    assert "top_k" in response.json()["prompts"][0]
    assert "top_p" in response.json()["prompts"][0]
    assert "objects" in response.json()["prompts"][0]
    assert isinstance(response.json()["prompts"][0]["id"], str)
    assert isinstance(response.json()["prompts"][0]["name"], str)
    assert isinstance(response.json()["prompts"][0]["prompt_text"], str)
    assert isinstance(response.json()["prompts"][0]["max_output_token"], int)
    assert isinstance(response.json()["prompts"][0]["temperature"], float)
    assert isinstance(response.json()["prompts"][0]["top_k"], int)
    assert isinstance(response.json()["prompts"][0]["top_p"], float)
    assert isinstance(response.json()["prompts"][0]["objects"], list)
    for obj in response.json()["prompts"][0]["objects"]:
        assert isinstance(obj, str)
    assert response.json()["prompts"][0]["name"] == "Prompt 2"

    response = await client.post(
        "/prompts/best_fit",
        headers=authorization_header,
        json={"objects": ["car", "bicycle"]},
    )
    assert response.status_code == 200
    assert "prompts" in response.json()
    assert isinstance(response.json()["prompts"], list)
    assert len(response.json()["prompts"]) == 1
    assert "id" in response.json()["prompts"][0]
    assert "name" in response.json()["prompts"][0]
    assert "prompt_text" in response.json()["prompts"][0]
    assert "max_output_token" in response.json()["prompts"][0]
    assert "temperature" in response.json()["prompts"][0]
    assert "top_k" in response.json()["prompts"][0]
    assert "top_p" in response.json()["prompts"][0]
    assert "objects" in response.json()["prompts"][0]
    assert isinstance(response.json()["prompts"][0]["id"], str)
    assert isinstance(response.json()["prompts"][0]["name"], str)
    assert isinstance(response.json()["prompts"][0]["prompt_text"], str)
    assert isinstance(response.json()["prompts"][0]["max_output_token"], int)
    assert isinstance(response.json()["prompts"][0]["temperature"], float)
    assert isinstance(response.json()["prompts"][0]["top_k"], int)
    assert isinstance(response.json()["prompts"][0]["top_p"], float)
    assert isinstance(response.json()["prompts"][0]["objects"], list)
    for obj in response.json()["prompts"][0]["objects"]:
        assert isinstance(obj, str)
    assert response.json()["prompts"][0]["name"] == "Prompt 3"


@pytest.mark.anyio
@pytest.mark.run(order=80)
async def test_prompts_delete_objects(
    client: AsyncClient,
    authorization_header: dict,
    context: dict,
) -> None:
    response = await client.delete(
        f"/prompts/{context['test_prompt_id']}/objects/{context['test_object_id']}",
        headers=authorization_header,
    )
    assert response.status_code == 200


@pytest.mark.anyio
@pytest.mark.run(order=81)
async def test_prompts_delete(
    client: AsyncClient,
    authorization_header: dict,
    context: dict,
) -> None:
    response = await client.delete(
        f"/prompts/{context['test_prompt_id']}", headers=authorization_header
    )
    assert response.status_code == 200
