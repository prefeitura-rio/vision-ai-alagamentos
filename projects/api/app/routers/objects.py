# -*- coding: utf-8 -*-
from functools import partial
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page
from fastapi_pagination.ext.tortoise import paginate as tortoise_paginate
from tortoise.fields import ReverseRelation

from app.dependencies import is_admin, is_agent
from app.models import Camera, Label, Object
from app.pydantic_models import (
    CameraOut,
    LabelIn,
    LabelOut,
    LabelsIn,
    LabelUpdate,
    ObjectIn,
    ObjectOut,
    User,
)
from app.utils import apply_to_list, transform_tortoise_to_pydantic

router = APIRouter(prefix="/objects", tags=["Objects"])


@router.get("", response_model=Page[ObjectOut])
async def get_objects(
    _: Annotated[User, Depends(is_agent)],
) -> Page[ObjectOut]:
    """Get a list of all objects."""

    async def get_labels(labels_relation: ReverseRelation) -> list[LabelOut]:
        labels: list[Label] = await labels_relation.all()
        return [
            LabelOut(
                id=label.id,
                value=label.value,
                criteria=label.criteria,
                identification_guide=label.identification_guide,
                text=label.text,
            )
            for label in labels
        ]

    return await tortoise_paginate(
        Object,
        transformer=partial(
            apply_to_list,
            fn=partial(
                transform_tortoise_to_pydantic,
                pydantic_model=ObjectOut,
                vars_map=[
                    ("id", "id"),
                    ("name", "name"),
                    ("slug", "slug"),
                    ("title", "title"),
                    ("explanation", "explanation"),
                    ("labels", ("labels", get_labels)),
                ],
            ),
        ),
    )


@router.post("", response_model=ObjectOut)
async def create_object(
    object_: ObjectIn,
    _: Annotated[User, Depends(is_admin)],
) -> ObjectOut:
    """Add a new object."""
    object = await Object.create(**object_.dict())
    return ObjectOut(
        id=object.id,
        name=object.name,
        slug=object.slug,
        title=object.title,
        explanation=object.explanation,
        labels=[],
    )


@router.delete("/{object_id}", response_model=ObjectOut)
async def delete_object(
    object_id: UUID,
    _: Annotated[User, Depends(is_admin)],
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
        title=object.title,
        explanation=object.explanation,
        labels=[
            LabelOut(
                id=label.id,
                value=label.value,
                criteria=label.criteria,
                identification_guide=label.identification_guide,
                text=label.text,
            )
            for label in await object.labels.all()
        ],
    )


@router.get("/{object_id}/labels", response_model=Page[LabelOut])
async def get_object_labels(
    object_id: UUID,
    _: Annotated[User, Depends(is_admin)],
) -> Page[LabelOut]:
    """Get a list of all labels for an object."""
    object = await Object.get_or_none(id=object_id)
    if object is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Object not found",
        )

    return await tortoise_paginate(
        object.labels,
        transformer=partial(
            apply_to_list,
            fn=partial(
                transform_tortoise_to_pydantic,
                pydantic_model=LabelOut,
                vars_map=[
                    ("id", "id"),
                    ("value", "value"),
                    ("criteria", "criteria"),
                    ("identification_guide", "identification_guide"),
                    ("text", "text"),
                ],
            ),
        ),
    )


@router.post("/{object_id}/labels", response_model=LabelOut)
async def add_label_to_object(
    object_id: UUID,
    label: LabelIn,
    _: Annotated[User, Depends(is_admin)],
) -> LabelOut:
    """Add a label to an object."""
    object = await Object.get_or_none(id=object_id)
    if object is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Object not found",
        )

    last_label = await Label.filter(object=object).order_by("-order").first()
    if not last_label:
        order = 0
    else:
        order = last_label.order + 1

    label_raw = await Label.create(object=object, order=order, **label.dict())
    return LabelOut(
        id=label_raw.id,
        value=label.value,
        criteria=label.criteria,
        identification_guide=label.identification_guide,
        text=label.text,
    )


@router.put("/{object_id}/labels/{label}", response_model=LabelOut)
async def update_object_label(
    object_id: UUID,
    label: str | UUID,
    label_: LabelUpdate,
    _: Annotated[User, Depends(is_admin)],
) -> LabelOut:
    """Update a label for an object."""
    # If `label` is a valid UUID, it's the label ID, otherwise it's the label value
    try:
        label_id = UUID(label)
        label_value = None
    except ValueError:
        label_id = None
        label_value = label
    if label_id:
        label_obj = await Label.get_or_none(id=label_id, object_id=object_id)
    elif label_value:
        label_obj = await Label.get_or_none(value=label_value, object_id=object_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid label",
        )
    if label_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Label not found",
        )
    if label_.value:
        label_obj.value = label_.value
    if label_.criteria:
        label_obj.criteria = label_.criteria
    if label_.identification_guide:
        label_obj.identification_guide = label_.identification_guide
    if label_.text:
        label_obj.text = label_.text
    await label_obj.save()
    return LabelOut(
        id=label_obj.id,
        value=label_obj.value,
        criteria=label_obj.criteria,
        identification_guide=label_obj.identification_guide,
        text=label_obj.text,
    )


@router.post("/{object_id}/labels/order", response_model=list[LabelOut])
async def order_object_label(
    object_id: UUID,
    data: LabelsIn,
    _: Annotated[User, Depends(is_admin)],
) -> list[LabelOut]:
    object = await Object.get_or_none(id=object_id)
    if object is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Object not found",
        )

    order = {label: index for index, label in enumerate(data.labels)}
    labels = await Label.filter(object=object).all()
    if len(labels) != len(data.labels):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must send all object labels",
        )

    for index, label in enumerate(labels):
        if label.value not in order:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must send all object labels",
            )

        labels[index].order = order[label.value]

    await Label.bulk_update(labels, fields=["order"])

    return sorted(
        [
            LabelOut(
                id=label.id,
                value=label.value,
                text=label.text,
                criteria=label.criteria,
                identification_guide=label.identification_guide,
            )
            for label in labels
        ],
        key=lambda label: order[label.value],
    )


@router.delete("/{object_id}/labels/{label}", response_model=LabelOut)
async def delete_object_label(
    object_id: UUID,
    label: str | UUID,
    _: Annotated[User, Depends(is_admin)],
) -> LabelOut:
    """Delete a label from an object."""
    # If `label` is a valid UUID, it's the label ID, otherwise it's the label value
    try:
        label_id = UUID(label)
        label_value = None
    except ValueError:
        label_id = None
        label_value = label
    if label_id:
        label_obj = await Label.get_or_none(id=label_id)
    elif label_value:
        label_obj = await Label.get_or_none(value=label_value, object_id=object_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid label",
        )
    if label_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Label not found",
        )
    await label_obj.delete()
    return LabelOut(
        id=label_obj.id,
        value=label_obj.value,
        criteria=label_obj.criteria,
        identification_guide=label_obj.identification_guide,
        text=label_obj.text,
    )


@router.post("/{object_id}/cameras/{camera_id}", response_model=CameraOut)
async def add_camera_to_object(
    object_id: UUID,
    camera_id: str,
    _: Annotated[User, Depends(is_admin)],
) -> CameraOut:
    """Add a camera to an object."""
    object = await Object.get_or_none(id=object_id)
    if object is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Object not found",
        )
    camera = await Camera.get_or_none(id=camera_id)
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )
    await object.cameras.add(camera)
    return CameraOut(
        id=camera.id,
        name=camera.name,
        rtsp_url=camera.rtsp_url,
        update_interval=camera.update_interval,
        latitude=camera.latitude,
        longitude=camera.longitude,
    )
