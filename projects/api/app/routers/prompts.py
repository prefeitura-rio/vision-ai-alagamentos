# -*- coding: utf-8 -*-
from functools import partial
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page
from fastapi_pagination.ext.tortoise import paginate as tortoise_paginate
from tortoise.fields import ReverseRelation

from app.dependencies import is_admin, is_agent
from app.models import Object, Prompt, PromptObject
from app.pydantic_models import (
    LabelOut,
    ObjectOut,
    ObjectsSlugIn,
    PromptIn,
    PromptOut,
    PromptsOut,
    User,
)
from app.utils import (
    apply_to_list,
    get_prompt_formatted_text,
    get_prompts_best_fit,
    transform_tortoise_to_pydantic,
)

router = APIRouter(prefix="/prompts", tags=["Prompts"])


@router.get("", response_model=Page[PromptOut])
async def get_prompts(
    _: Annotated[User, Depends(is_admin)],
) -> Page[PromptOut]:
    """Get a list of all prompts."""

    async def get_objects(objects_relation: ReverseRelation) -> list[str]:
        return (
            await Object.filter(prompts__in=await objects_relation.all())
            .all()
            .order_by("prompts__order")
            .values_list("slug", flat=True)
        )

    return await tortoise_paginate(
        Prompt,
        transformer=partial(
            apply_to_list,
            fn=partial(
                transform_tortoise_to_pydantic,
                pydantic_model=PromptOut,
                vars_map=[
                    ("id", "id"),
                    ("name", "name"),
                    ("model", "model"),
                    ("prompt_text", "prompt_text"),
                    ("max_output_token", "max_output_token"),
                    ("temperature", "temperature"),
                    ("top_k", "top_k"),
                    ("top_p", "top_p"),
                    ("objects", ("objects", get_objects)),
                ],
            ),
        ),
    )


@router.post("", response_model=PromptOut)
async def create_prompt(
    prompt_: PromptIn,
    _: Annotated[User, Depends(is_admin)],
) -> PromptOut:
    """Add a new prompt."""
    prompt = await Prompt.create(**prompt_.dict())
    return PromptOut(
        id=prompt.id,
        name=prompt.name,
        model=prompt.model,
        prompt_text=prompt.prompt_text,
        max_output_token=prompt.max_output_token,
        temperature=prompt.temperature,
        top_k=prompt.top_k,
        top_p=prompt.top_p,
        objects=[],
    )


@router.get("/{prompt_id}", response_model=PromptOut)
async def get_prompt(
    prompt_id: UUID,
    _: Annotated[User, Depends(is_agent)],
) -> PromptOut:
    """Get a prompt by id."""
    prompt = await Prompt.get_or_none(id=prompt_id)
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    objects = (
        await Object.filter(prompts__prompt=prompt)
        .order_by("prompts__order")
        .all()
        .values_list("slug", flat=True)
    )
    return PromptOut(
        id=prompt.id,
        name=prompt.name,
        model=prompt.model,
        prompt_text=prompt.prompt_text,
        max_output_token=prompt.max_output_token,
        temperature=prompt.temperature,
        top_k=prompt.top_k,
        top_p=prompt.top_p,
        objects=objects,
    )


@router.put("/{prompt_id}", response_model=PromptOut)
async def update_prompt(
    prompt_id: UUID,
    prompt_: PromptIn,
    _: Annotated[User, Depends(is_admin)],
) -> PromptOut:
    """Update a prompt."""
    prompt = await Prompt.get_or_none(id=prompt_id)
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    await prompt.update_from_dict(prompt_.dict()).save()
    objects = (
        await Object.filter(prompts__prompt=prompt)
        .order_by("prompts__order")
        .all()
        .values_list("slug", flat=True)
    )
    return PromptOut(
        id=prompt.id,
        name=prompt.name,
        model=prompt.model,
        prompt_text=prompt.prompt_text,
        max_output_token=prompt.max_output_token,
        temperature=prompt.temperature,
        top_k=prompt.top_k,
        top_p=prompt.top_p,
        objects=objects,
    )


@router.delete("/{prompt_id}")
async def delete_prompt(
    prompt_id: UUID,
    _: Annotated[User, Depends(is_admin)],
) -> None:
    """Delete a prompt."""
    prompt = await Prompt.get_or_none(id=prompt_id)
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    await prompt.delete()


@router.get("/{prompt_id}/objects", response_model=list[ObjectOut])
async def get_prompt_objects(
    prompt_id: UUID,
    _: Annotated[User, Depends(is_agent)],
) -> list[ObjectOut]:
    """Get a prompt's objects."""
    prompt = await Prompt.get_or_none(id=prompt_id)
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    return [
        ObjectOut(
            id=object_.id,
            name=object_.name,
            slug=object_.slug,
            title=object_.title,
            explanation=object_.explanation,
            labels=[
                LabelOut(
                    id=label.id,
                    value=label.value,
                    criteria=label.criteria,
                    identification_guide=label.identification_guide,
                )
                for label in await object_.labels.all()
            ],
        )
        for object_ in await Object.filter(prompts__prompt=prompt).order_by("prompts__order").all()
    ]


@router.post("/{prompt_id}/objects", response_model=ObjectOut)
async def add_prompt_object(
    prompt_id: UUID,
    object_id: UUID,
    _: Annotated[User, Depends(is_admin)],
) -> ObjectOut:
    """Add an object to a prompt."""
    prompt = await Prompt.get_or_none(id=prompt_id)
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    object_ = await Object.get_or_none(id=object_id)
    if object_ is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")

    order = 0
    prompt_object = await PromptObject.filter(prompt=prompt).order_by("-order").first()
    if prompt_object is not None:
        order = prompt_object.order + 1

    await PromptObject.create(prompt=prompt, object=object_, order=order)

    return ObjectOut(
        id=object_.id,
        name=object_.name,
        slug=object_.slug,
        title=object_.title,
        explanation=object_.explanation,
        labels=[
            LabelOut(
                id=label.id,
                value=label.value,
                criteria=label.criteria,
                identification_guide=label.identification_guide,
            )
            for label in await object_.labels.all()
        ],
    )


@router.post("/{prompt_id}/objects/order", response_model=ObjectOut)
async def order_prompt_object(
    prompt_id: UUID,
    objects_in: ObjectsSlugIn,
    _: Annotated[User, Depends(is_admin)],
) -> PromptOut:
    """Add an object to a prompt."""
    prompt = await Prompt.get_or_none(id=prompt_id)
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")

    object_slugs = objects_in.objects
    objects = (
        await Object.filter(prompts__prompt=prompt)
        .all()
        .select_related("prompts")
        .values("prompts__id", "slug")
    )

    if len(object_slugs) != len(objects):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Must contain all object slugs in order"
        )

    for object_ in objects:
        if object_["slug"] not in object_slugs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must contain all object slugs in order",
            )

    object_order = {v: k for k, v in enumerate(object_slugs)}
    slug_by_prompt = {object_["prompts__id"]: object_["slug"] for object_ in objects}
    prompt_objects = await PromptObject.filter(prompt=prompt).all()

    for i in range(len(prompt_objects)):
        prompt_objects[i].order = object_order[slug_by_prompt[prompt_objects[i].id]]

    await PromptObject.bulk_update(prompt_objects, fields=["order"])

    return PromptOut(
        id=prompt.id,
        name=prompt.name,
        model=prompt.model,
        prompt_text=prompt.prompt_text,
        max_output_token=prompt.max_output_token,
        temperature=prompt.temperature,
        top_k=prompt.top_k,
        top_p=prompt.top_p,
        objects=object_slugs,
    )


@router.delete("/{prompt_id}/objects/{object_id}")
async def remove_prompt_object(
    prompt_id: UUID,
    object_id: UUID,
    _: Annotated[User, Depends(is_admin)],
) -> None:
    """Remove an object from a prompt."""
    prompt = await Prompt.get_or_none(id=prompt_id)
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    object_ = await Object.get_or_none(id=object_id)
    if object_ is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
    await PromptObject.filter(prompt=prompt, object=object_).delete()


@router.post("/best_fit", response_model=PromptsOut)
async def get_best_fit_prompts(
    request: ObjectsSlugIn,
    _: Annotated[User, Depends(is_agent)],
) -> PromptsOut:
    """Get the best fit prompts for a list of objects."""
    object_slugs = request.objects

    objects: list[Object] = []
    for object_slug in object_slugs:
        object_ = await Object.get_or_none(slug=object_slug)
        if object_ is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
        objects.append(object_)

    prompts = await get_prompts_best_fit(objects=objects)
    prompts_formatted_text = []
    for prompt in prompts:
        prompts_formatted_text.append(
            await get_prompt_formatted_text(prompt=prompt, objects=objects)
        )
    ret_prompts = []
    for prompt, prompt_formatted_text in zip(prompts, prompts_formatted_text):
        object_slugs = (
            await Object.filter(prompts__prompt=prompt)
            .all()
            .order_by("prompts__order")
            .values_list("slug", flat=True)
        )
        ret_prompts.append(
            PromptOut(
                id=prompt.id,
                name=prompt.name,
                model=prompt.model,
                objects=object_slugs,
                prompt_text=prompt_formatted_text,
                max_output_token=prompt.max_output_token,
                temperature=prompt.temperature,
                top_k=prompt.top_k,
                top_p=prompt.top_p,
            )
        )
    return PromptsOut(
        prompts=ret_prompts,
    )
