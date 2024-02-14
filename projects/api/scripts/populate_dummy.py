# -*- coding: utf-8 -*-
from app.db import TORTOISE_ORM
from app.models import Camera, Identification, Object, Prompt
from tortoise import Tortoise, run_async


async def run():
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()

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
        {"name": "Person", "slug": "person"},
        {"name": "Car", "slug": "car"},
        {"name": "Bicycle", "slug": "bicycle"},
    ]
    objects = []
    for object in object_data:
        objects.append(await Object.create(**object))

    prompt_data = [
        {
            "name": "Prompt 1",
            "prompt_text": "Prompt 1 text",
            "max_output_token": 100,
            "temperature": 0.5,
            "top_k": 0,
            "top_p": 0.9,
        },
        {
            "name": "Prompt 2",
            "prompt_text": "Prompt 2 text",
            "max_output_token": 100,
            "temperature": 0.5,
            "top_k": 0,
            "top_p": 0.9,
        },
        {
            "name": "Prompt 3",
            "prompt_text": "Prompt 3 text",
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
        for object in objects[: i + 1]:
            await prompt.objects.add(object)

    identification_data = [
        {
            "camera": cameras[0],
            "object": objects[0],
        },
        {
            "camera": cameras[0],
            "object": objects[1],
        },
        {
            "camera": cameras[1],
            "object": objects[1],
        },
        {
            "camera": cameras[1],
            "object": objects[2],
        },
        {
            "camera": cameras[2],
            "object": objects[2],
        },
        {
            "camera": cameras[2],
            "object": objects[0],
        },
    ]
    for identification in identification_data:
        await Identification.create(**identification)

    await Tortoise.close_connections()


if __name__ == "__main__":
    run_async(run())
