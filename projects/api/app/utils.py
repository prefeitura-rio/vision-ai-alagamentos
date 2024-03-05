# -*- coding: utf-8 -*-
import asyncio
import base64
import inspect
import json
from asyncio import Task
from typing import Any, Callable

import nest_asyncio
from app import config
from app.models import Label, Object, Prompt
from google.cloud import pubsub
from google.oauth2 import service_account
from pydantic import BaseModel
from tortoise.functions import Count
from tortoise.models import Model
from vision_ai.base.shared_models import Output, OutputFactory


def _to_task(future, as_task, loop):
    if not as_task or isinstance(future, Task):
        return future
    return loop.create_task(future)


def apply_to_list(lst: list[Any], fn: Callable) -> list[Any]:
    """
    Applies a function to a whole list and returns the result.
    """
    return [fn(item) for item in lst]


def asyncio_run(future, as_task=True):
    """
    A better implementation of `asyncio.run`.

    :param future: A future or task or call of an async method.
    :param as_task: Forces the future to be scheduled as task (needed for e.g. aiohttp).
    """

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # no event loop running:
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(_to_task(future, as_task, loop))
    else:
        nest_asyncio.apply(loop)
        return asyncio.run(_to_task(future, as_task, loop))


def fn_is_async(fn: Callable) -> bool:
    """
    Checks if a function is async.

    Args:
        fn (Callable): The function to check.

    Returns:
        bool: True if the function is async, False otherwise.
    """
    return inspect.iscoroutinefunction(fn) or inspect.isasyncgenfunction(fn)


def get_gcp_credentials(
    scopes: list[str] | None = None,
) -> service_account.Credentials:
    """
    Gets credentials from env vars
    """
    env: str = config.GCP_SERVICE_ACCOUNT_CREDENTIALS
    if not env:
        raise ValueError("GCP_SERVICE_ACCOUNT_CREDENTIALS env var not set!")
    info: dict = json.loads(base64.b64decode(env))
    cred: service_account.Credentials = service_account.Credentials.from_service_account_info(info)
    if scopes:
        cred = cred.with_scopes(scopes)
    return cred


async def get_objects_table(objects: list[Object]) -> str:
    """
    Fetches all `Label` objects for the provided `objects` and return
    a markdown table with the following format:

    | object | criteria | identification_guide | label |
    | ------ | -------- | -------------------- | ----- |
    | ...    | ...      | ...                  | ...   |

    Args:
        objects (list[Object]): The objects to fetch.

    Returns:
        str: The markdown table.
    """
    # Fetch all labels for the objects
    objects_id = [object_.id for object_ in objects]
    raw_labels = (
        await Label.filter(object_id__in=objects_id)
        .all()
        .select_related("object__slug")
        .values("id", "criteria", "identification_guide", "value", "object__slug")
    )

    # dont use dict[str, dict[str, str]] to preserve labels order
    labels: list[dict[str, str]] = []
    labels_id: list[str] = []
    for label in raw_labels:
        if label["id"] not in labels_id:
            labels.append(label)
            labels_id.append(label["id"])

    # Create the header
    header = "| object | criteria | identification_guide | label |\n"
    header += "| ------ | -------- | -------------------- | ----- |\n"

    # Create the rows
    rows = ""
    for label in labels:
        slug = label["object__slug"]

        if slug != "image_description" and label["value"] == "null":
            continue

        rows += f"| {slug} | {label['criteria']} | {label['identification_guide']} | {label['value']} |\n"  # noqa

    # Return the table
    return header + rows


def get_output_schema_and_sample() -> tuple[str, str]:
    """
    Gets the output schema and sample for the vision AI model.

    Returns:
        tuple[str, str]: The output schema and sample.
    """
    output_schema = Output.schema_json(indent=4)
    output_sample = json.dumps(OutputFactory.generate_sample().dict(), indent=4)
    return output_schema, output_sample


async def get_prompt_formatted_text(prompt: Prompt, objects: list[Object]) -> str:
    """
    Gets the full text of a prompt.

    Args:
        prompt (Prompt): The prompt.
        objects (list[Object]): The objects to fetch.

    Returns:
        str: The full text of the prompt.
    """
    # Filter object slugs that are in the prompt objects
    prompt_slugs = await Object.filter(prompts__prompt=prompt).all().values_list("slug", flat=True)
    objects_filtered = [object_ for object_ in objects if object_.slug in prompt_slugs]
    objects_table_md = await get_objects_table(objects_filtered)
    output_schema, output_example = get_output_schema_and_sample()
    template = prompt.prompt_text
    template = template.format(
        objects_table_md=objects_table_md,
        output_schema=output_schema,
        output_example=output_example,
    )
    return template


async def get_prompts_best_fit(objects: list[Object], one: bool = False) -> list[Prompt]:
    """
    Gets the best fit prompts for a list of objects.

    Args:
        objects (list[Object]): The objects to fetch.
        one bool = false: Return only the best prompt

    Returns:
        list[Prompt]: The best fit prompts.
    """
    objects_id = [object_.id for object_ in objects]

    # Rank prompts id by number of objects in common
    prompts = (
        await Prompt.filter(objects__object_id__in=objects_id)
        .group_by("id", "name")
        .annotate(object_count=Count("objects__object_id"))
        .order_by("-object_count", "name")
        .all()
    )

    if len(prompts) == 0:
        return []

    if one:
        return [prompts[0]]

    final_prompts: list[Prompt] = []
    covered_objects: list[Object] = []

    for prompt in prompts:
        prompt_objects = await Object.filter(prompts__prompt=prompt).all()
        if not set(prompt_objects).intersection(set(covered_objects)):
            final_prompts.append(prompt)
            covered_objects += list(prompt_objects)

    return final_prompts


def get_pubsub_client() -> pubsub.PublisherClient:
    """
    Get a PubSub client with the credentials from the environment.

    Returns:
        storage.Client: The GCS client.
    """
    credentials = get_gcp_credentials(scopes=["https://www.googleapis.com/auth/pubsub"])
    return pubsub.PublisherClient(credentials=credentials)


def publish_message(
    *,
    data: dict[str, str],
    project_id: str = config.GCP_PUBSUB_PROJECT_ID,
    topic: str = config.GCP_PUBSUB_TOPIC_NAME,
):
    """
    Publishes a message to a PubSub topic.

    Args:
        data (dict[str, str]): The data to publish.
        project_id (str): The project id.
        topic (str): The topic name.
    """
    client = get_pubsub_client()
    topic_name = f"projects/{project_id}/topics/{topic}"
    byte_data = json.dumps(data, default=str).encode("utf-8")
    future = client.publish(topic_name, byte_data)
    return future.result()


def slugify(text: str) -> str:
    """
    Slugifies a string.

    Args:
        text (str): The string to slugify.

    Returns:
        str: The slugified string.
    """
    return text.lower().replace(" ", "-").replace("_", "-").replace(".", "-").strip()


def transform_tortoise_to_pydantic(
    tortoise_model: Model,
    pydantic_model: BaseModel,
    vars_map: list[tuple[str, str | tuple[str, Callable]]],
) -> BaseModel:
    """
    Transform a Tortoise ORM model to a Pydantic model using a variable mapping.

    Args:
        tortoise_model (Model): The Tortoise ORM model to transform.
        pydantic_model (BaseModel): The Pydantic model to transform into.
        vars_map (dict[str, str]): A dictionary mapping Tortoise ORM variable names
                                   to Pydantic variable names.

    Returns:
        BaseModel: An instance of the Pydantic model with values from the Tortoise model.
    """
    # Create a dictionary to store Pydantic field values
    pydantic_values = {}

    # Iterate through the variable mapping
    for tortoise_var, pydantic_var in vars_map:
        # Get the value from the Tortoise model
        tortoise_value = getattr(tortoise_model, tortoise_var, None)

        # If pydanctic_var is a tuple, it means that we need to apply a function to the value
        if isinstance(pydantic_var, tuple):
            pydantic_var, fn = pydantic_var
            if fn_is_async(fn):
                tortoise_value = asyncio_run(fn(tortoise_value))
            else:
                tortoise_value = fn(tortoise_value)

        # Set the value in the Pydantic dictionary
        pydantic_values[pydantic_var] = tortoise_value

    # Create an instance of the Pydantic model with the transformed values
    transformed_pydantic_model = pydantic_model(**pydantic_values)

    return transformed_pydantic_model
