# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
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


class BigParams(Params):
    size: int = Query(100, ge=1, le=3000)


class BigPage(Page[IdentificationAIOut]):
    __params_type__ = BigParams


@router.get("/ai", response_model=BigPage)
async def get_ai_identifications(
    user: Annotated[User, Depends(is_human)],
    params: BigParams = Depends(),
    minute_interval: int = 30,
) -> Page[IdentificationAIOut]:
    interval = datetime.now() - timedelta(minutes=minute_interval)
    offset = params.size * (params.page - 1)

    indentificateds = (
        await UserIdentification.all()
        .filter(username=user.name, timestamp__gte=interval)
        .values_list("identification__id", flat=True)
    )

    count = (
        await Identification.all()
        .filter(timestamp__gte=interval, id__not_in=indentificateds)
        .count()
    )

    identifications = (
        await Identification.all()
        .order_by("snapshot__timestamp", "timestamp")
        .filter(timestamp__gte=interval, id__not_in=indentificateds)
        .limit(params.size)
        .offset(offset)
        .values(
            "id",
            "snapshot__public_url",
            "snapshot__camera__id",
            "label__value",
            "label__text",
            "label__object__id",
            "label__object__slug",
            "label__object__title",
            "label__object__question",
            "label__object__explanation",
            "timestamp",
            "label_explanation",
        )
    )

    out = [
        IdentificationAIOut(
            id=identification["id"],
            object=identification["label__object__slug"],
            title=identification["label__object__title"],
            question=identification["label__object__question"],
            explanation=identification["label__object__explanation"],
            timestamp=identification["timestamp"],
            label=identification["label__value"],
            label_text=identification["label__text"],
            ai_explanation=identification["label__value"],
            snapshot_url=identification["snapshot__public_url"],
        )
        for identification in identifications
    ]

    return create_page(out, total=count, params=params)


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
        question=object_.question,
        explanation=object_.explanation,
        timestamp=user_identification.timestamp,
        label=label.value,
        label_text=label.text,
        label_explanation="",
        snapshot=SnapshotOut(
            id=identification.snapshot.id,
            image_url=identification.snapshot.public_url,
            camera_id=identification.snapshot.camera.id,
            timestamp=identification.snapshot.timestamp,
        ),
    )
