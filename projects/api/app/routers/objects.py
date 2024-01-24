# -*- coding: utf-8 -*-
from functools import partial
from typing import Annotated

from app.dependencies import get_caller, is_admin
from app.models import Object
from app.pydantic_models import APICaller, ObjectIn, ObjectOut
from app.utils import apply_to_list, transform_tortoise_to_pydantic
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page
from fastapi_pagination.ext.tortoise import paginate as tortoise_paginate

router = APIRouter(prefix="/objects", tags=["Objects"])


@router.get("", response_model=Page[ObjectOut])
async def get_objects(
    _: Annotated[APICaller, Depends(get_caller)],  # TODO: Review permissions here
) -> Page[ObjectOut]:
    """Get a list of all objects."""
    return await tortoise_paginate(
        Object,
        transformer=partial(
            apply_to_list,
            fn=partial(
                transform_tortoise_to_pydantic,
                pydantic_model=ObjectOut,
                vars_map={
                    "id": "id",
                    "name": "name",
                    "slug": "slug",
                },
            ),
        ),
    )


@router.post("", response_model=ObjectOut)
async def create_object(
    object_: ObjectIn,
    _=Depends(is_admin),
) -> ObjectOut:
    """Add a new object."""
    object = await Object.create(**object_.dict())
    return ObjectOut(
        id=object.id,
        name=object.name,
        slug=object.slug,
    )


@router.delete("/{object_id}", response_model=ObjectOut)
async def delete_object(
    object_id: int,
    _=Depends(is_admin),
) -> ObjectOut:
    """Delete an object."""
    object = await Object.get_or_none(id=object_id)
    if object is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Object not found",
        )
    await object.delete()
    return ObjectOut(
        id=object.id,
        name=object.name,
        slug=object.slug,
    )
