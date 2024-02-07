# -*- coding: utf-8 -*-
from functools import partial
from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page
from fastapi_pagination.ext.tortoise import paginate as tortoise_paginate
from tortoise.fields import ReverseRelation

from app.dependencies import get_caller, is_admin
from app.models import Object, Prompt
from app.pydantic_models import (
    APICaller,
    LabelOut,
    ObjectOut,
    ObjectsSlugIn,
    PromptIn,
    PromptOut,
    PromptsOut,
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
    _=Depends(is_admin),
) -> Page[PromptOut]:
    """Get a list of all prompts."""

    async def get_objects(objects_relation: ReverseRelation) -> List[str]:
        objects: List[Object] = await objects_relation.all()
        return [object_.slug for object_ in objects]

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
    _=Depends(is_admin),
) -> PromptOut:
    """Add a new prompt."""
    prompt = await Prompt.create(**prompt_.dict())
    objects: List[str] = []
    for object_ in await prompt.objects.all():
        objects.append(object_.slug)
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


@router.get("/{prompt_id}", response_model=PromptOut)
async def get_prompt(
    prompt_id: UUID,
    _: Annotated[APICaller, Depends(get_caller)],  # TODO: Review permissions here
) -> PromptOut:
    """Get a prompt by id."""
    prompt = await Prompt.get_or_none(id=prompt_id)
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    objects: List[str] = []
    for object_ in await prompt.objects.all():
        objects.append(object_.slug)
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
    _=Depends(is_admin),
) -> PromptOut:
    """Update a prompt."""
    prompt = await Prompt.get_or_none(id=prompt_id)
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    await prompt.update_from_dict(prompt_.dict()).save()
    objects: List[str] = []
    for object_ in await prompt.objects.all():
        objects.append(object_.slug)
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
    _=Depends(is_admin),
) -> None:
    """Delete a prompt."""
    prompt = await Prompt.get_or_none(id=prompt_id)
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    await prompt.delete()


@router.get("/{prompt_id}/objects", response_model=List[ObjectOut])
async def get_prompt_objects(
    prompt_id: UUID,
    _: Annotated[APICaller, Depends(get_caller)],  # TODO: Review permissions here
) -> List[ObjectOut]:
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
        for object_ in await prompt.objects.all()
    ]


@router.post("/{prompt_id}/objects", response_model=ObjectOut)
async def add_prompt_object(
    prompt_id: UUID,
    object_id: UUID,
    _=Depends(is_admin),
) -> ObjectOut:
    """Add an object to a prompt."""
    prompt = await Prompt.get_or_none(id=prompt_id)
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    object_ = await Object.get_or_none(id=object_id)
    if object_ is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
    await prompt.objects.add(object_)
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


@router.delete("/{prompt_id}/objects/{object_id}")
async def remove_prompt_object(
    prompt_id: UUID,
    object_id: UUID,
    _=Depends(is_admin),
) -> None:
    """Remove an object from a prompt."""
    prompt = await Prompt.get_or_none(id=prompt_id)
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    object_ = await Object.get_or_none(id=object_id)
    if object_ is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
    await prompt.objects.remove(object_)


@router.post("/best_fit", response_model=PromptsOut)
async def get_best_fit_prompts(
    request: ObjectsSlugIn,
    _: Annotated[APICaller, Depends(get_caller)],  # TODO: Review permissions here
) -> PromptsOut:
    """Get the best fit prompts for a list of objects."""
    object_slugs = request.objects
    prompts = await get_prompts_best_fit(object_slugs=object_slugs)
    prompts_formatted_text = []
    for prompt in prompts:
        prompts_formatted_text.append(
            await get_prompt_formatted_text(prompt=prompt, object_slugs=object_slugs)
        )
    ret_prompts = []
    for prompt, prompt_formatted_text in zip(prompts, prompts_formatted_text):
        objects = []
        for object_ in await prompt.objects.all():
            objects.append(object_.slug)
        ret_prompts.append(
            PromptOut(
                id=prompt.id,
                name=prompt.name,
                model=prompt.model,
                objects=objects,
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
