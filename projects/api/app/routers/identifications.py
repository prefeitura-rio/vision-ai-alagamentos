# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page, create_page
from fastapi_pagination.default import Params

from app.dependencies import is_human
from app.models import Identification, Label, UserIdentification
from app.pydantic_models import (
    IdentificationAIOut,
    IdentificationHumanIN,
    IdentificationOut,
    SnapshotOut,
    User,
)

router = APIRouter(prefix="/identifications", tags=["identifications"])


@router.get("/ai", response_model=Page[IdentificationAIOut])
async def get_ai_identifications(
    user: Annotated[User, Depends(is_human)],
    params: Params = Depends(),
    minute_interval: int = 30,
) -> Page[IdentificationAIOut]:
    interval = datetime.now() - timedelta(minutes=minute_interval)

    indentificateds = (
        await UserIdentification.all()
        .filter(username=user.name, timestamp__gte=interval)
        .values_list("identification__id", flat=True)
    )

    identifications = (
        await Identification.all()
        .order_by("timestamp")
        .filter(timestamp__gte=interval, id__not_in=indentificateds)
        .values(
            "id",
            "snapshot__public_url",
            "snapshot__camera__id",
            "label__value",
            "label__object__id",
            "label__object__slug",
            "label__object__title",
            "label__object__explanation",
            "timestamp",
            "label_explanation",
        )
    )

    objects_ids = list(
        set([identification["label__object__id"] for identification in identifications])
    )
    labels = await Label.all().filter(object__id__in=objects_ids).values("value", "object__slug")
    possible_labels: dict[str, list[str]] = {}

    for label in labels:
        slug = label["object__slug"]
        value = label["value"]

        if slug not in possible_labels:
            possible_labels[slug] = [value]
        else:
            possible_labels[slug].append(value)

    out = [
        IdentificationAIOut(
            id=identification["id"],
            object=identification["label__object__slug"],
            title=identification["label__object__title"],
            explanation=identification["label__object__explanation"],
            timestamp=identification["timestamp"],
            label=identification["label__value"],
            possible_labels=possible_labels[identification["label__object__slug"]],
            ai_explanation=identification["label__value"],
            snapshot_url=identification["snapshot__public_url"],
        )
        for identification in identifications
    ]

    return create_page(out, total=len(out), params=params)


@router.post("", response_model=IdentificationOut)
async def create_user_identification(
    user: Annotated[User, Depends(is_human)],
    data: IdentificationHumanIN,
) -> IdentificationOut:
    identification = await Identification.get_or_none(id=data.identification_id).prefetch_related(
        "label__object", "snapshot", "snapshot__camera"
    )
    if identification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Identification not found."
        )

    object_ = identification.label.object
    print(object_.name)
    print(data.label)

    label = await Label.get_or_none(object=object_, value=data.label)
    if label is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Label not found.")

    user_identification = await UserIdentification.create(
        timestamp=datetime.now(),
        username=user.name,
        label=label,
        identification=identification,
    )

    return IdentificationOut(
        id=identification.id,
        object=object_.slug,
        title=object_.title,
        explanation=object_.explanation,
        timestamp=user_identification.timestamp,
        label=data.label,
        label_explanation="",
        snapshot=SnapshotOut(
            id=identification.snapshot.id,
            image_url=identification.snapshot.public_url,
            camera_id=identification.snapshot.camera.id,
            timestamp=identification.snapshot.timestamp,
        ),
    )
