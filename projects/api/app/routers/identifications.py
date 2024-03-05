# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi_pagination import Page, create_page
from fastapi_pagination.default import Params
from tortoise import connections
from tortoise.expressions import Q

from app.dependencies import get_user, is_admin, is_human
from app.models import (
    Identification,
    IdentificationMaker,
    Label,
    Snapshot,
    UserIdentification,
)
from app.pydantic_models import (
    Aggregation,
    HumanIdentificationAggregation,
    IaIdentificationAggregation,
    IdentificationHumanIN,
    IdentificationMarkerDelete,
    IdentificationMarkerIn,
    IdentificationMarkerOut,
    IdentificationOut,
    SnapshotOut,
    User,
)

router = APIRouter(prefix="/identifications", tags=["identifications"])


class BigParams(Params):
    size: int = Query(100, ge=1, le=3000)


class BigPage(Page[IdentificationOut]):
    __params_type__ = BigParams


@router.get("/ai", response_model=BigPage)
async def get_ai_identifications(
    user: Annotated[User, Depends(is_human)],
    params: BigParams = Depends(),
) -> Page[IdentificationOut]:
    offset = params.size * (params.page - 1)

    indentificateds = (
        await UserIdentification.all()
        .filter(username=user.name)
        .values_list("identification_id", flat=True)
    )

    ids = (
        await IdentificationMaker.all()
        .filter(identification_id__not_in=indentificateds)
        .values_list("identification_id", flat=True)
    )

    count = len(ids)

    identifications = (
        await Identification.all()
        .filter(id__in=ids)
        .order_by("snapshot__timestamp", "timestamp")
        .limit(params.size)
        .offset(offset)
        .prefetch_related("snapshot", "snapshot__camera", "label", "label__object")
    )

    out = [
        IdentificationOut(
            id=identification.id,
            object=identification.label.object.slug,
            title=identification.label.object.title,
            question=identification.label.object.question,
            explanation=identification.label.object.explanation,
            timestamp=identification.timestamp,
            label=identification.label.value,
            label_text=identification.label.text,
            label_explanation=identification.label_explanation,
            snapshot=SnapshotOut(
                id=identification.snapshot.id,
                camera_id=identification.snapshot.camera.id,
                image_url=identification.snapshot.public_url,
                timestamp=identification.snapshot.timestamp,
            ),
        )
        for identification in identifications
    ]

    return create_page(out, total=count, params=params)


@router.get("/ai/all", response_model=BigPage)
async def get_all_ai_identifications(
    _: Annotated[User, Depends(is_human)],
    params: BigParams = Depends(),
) -> Page[IdentificationOut]:
    offset = params.size * (params.page - 1)

    ids = await IdentificationMaker.all().values_list("identification_id", flat=True)

    count = len(ids)

    identifications = (
        await Identification.all()
        .filter(id__in=ids)
        .order_by("snapshot__timestamp", "timestamp")
        .limit(params.size)
        .offset(offset)
        .prefetch_related("snapshot", "snapshot__camera", "label", "label__object")
    )

    out = [
        IdentificationOut(
            id=identification.id,
            object=identification.label.object.slug,
            title=identification.label.object.title,
            question=identification.label.object.question,
            explanation=identification.label.object.explanation,
            timestamp=identification.timestamp,
            label=identification.label.value,
            label_text=identification.label.text,
            label_explanation=identification.label_explanation,
            snapshot=SnapshotOut(
                id=identification.snapshot.id,
                camera_id=identification.snapshot.camera.id,
                image_url=identification.snapshot.public_url,
                timestamp=identification.snapshot.timestamp,
            ),
        )
        for identification in identifications
    ]

    return create_page(out, total=count, params=params)


@router.get("", response_model=BigPage)
async def get_identifications(
    _: Annotated[User, Depends(get_user)],
    params: BigParams = Depends(),
    minute_interval: int = 30,
) -> Page[IdentificationOut]:
    interval = datetime.now() - timedelta(minutes=minute_interval)
    offset = params.size * (params.page - 1)

    count = await Identification.all().filter(snapshot__timestamp__gte=interval).count()

    identifications = (
        await Identification.all()
        .order_by("snapshot__timestamp", "timestamp")
        .filter(snapshot__timestamp__gte=interval)
        .limit(params.size)
        .offset(offset)
        .prefetch_related("snapshot", "snapshot__camera", "label", "label__object")
    )

    out = [
        IdentificationOut(
            id=identification.id,
            object=identification.label.object.slug,
            title=identification.label.object.title,
            question=identification.label.object.question,
            explanation=identification.label.object.explanation,
            timestamp=identification.timestamp,
            label=identification.label.value,
            label_text=identification.label.text,
            label_explanation=identification.label_explanation,
            snapshot=SnapshotOut(
                id=identification.snapshot.id,
                camera_id=identification.snapshot.camera.id,
                image_url=identification.snapshot.public_url,
                timestamp=identification.snapshot.timestamp,
            ),
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

    user_identification = await UserIdentification.get_or_none(
        username=user.name, identification=identification
    )
    if user_identification is None:
        user_identification = await UserIdentification.create(
            timestamp=datetime.now(),
            username=user.name,
            label=label,
            identification=identification,
        )
        tags = ["human"]
        marker = await IdentificationMaker.filter(identification=identification).get_or_none()
        if marker is None:
            await IdentificationMaker.create(identification=identification, tags=tags)
        else:
            if marker.tags is None:
                marker.tags = tags
            else:
                marker.tags = list(set(marker.tags + tags))
            await marker.save()
    else:
        user_identification.label = label
        await user_identification.save()

    return IdentificationOut(
        id=identification.id,
        object=object_.slug,
        title=object_.title,
        question=object_.question,
        explanation=object_.explanation,
        timestamp=user_identification.timestamp,
        label=label.value,
        label_text=label.text,
        label_explanation="Human Identification",
        snapshot=SnapshotOut(
            id=identification.snapshot.id,
            image_url=identification.snapshot.public_url,
            camera_id=identification.snapshot.camera.id,
            timestamp=identification.snapshot.timestamp,
        ),
    )


@router.post("/marker", response_model=IdentificationMarkerOut)
async def create_marker(
    _: Annotated[User, Depends(is_admin)],
    data: IdentificationMarkerIn,
) -> IdentificationMarkerOut:
    snapshot_ids = []
    if data.identifications_id is not None and len(data.identifications_id) > 0:
        identifications = (
            await Identification.filter(id__in=data.identifications_id)
            .all()
            .prefetch_related("snapshot")
        )
        if len(identifications) != len(data.identifications_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Some identifications id not found."
            )
        snapshot_ids += list(
            set([identification.snapshot.id for identification in identifications])
        )

    if data.snapshots_id is not None and len(data.snapshots_id) > 0:
        ids = await Snapshot.filter(id__in=data.snapshots_id).all().values_list("id", flat=True)
        if len(ids) != len(data.snapshots_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Some snapshots id not found."
            )
        snapshot_ids = list(set(snapshot_ids + ids))

    if len(snapshot_ids) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must send indetifications or snapshots ids",
        )

    identifications = await Identification.filter(snapshot_id__in=snapshot_ids).all()
    exist = (
        await IdentificationMaker.filter(
            identification_id__in=[identification.id for identification in identifications]
        )
        .all()
        .prefetch_related("identification")
    )
    exist_ids = [marker.identification.id for marker in exist]
    identifications = [
        identification for identification in identifications if identification.id not in exist_ids
    ]

    await IdentificationMaker.bulk_create(
        [
            IdentificationMaker(identification=identification, tags=data.tags)
            for identification in identifications
        ]
    )

    if data.tags is not None and len(exist) > 0:
        for index, marker in enumerate(exist):
            tags: list[str] = data.tags
            if marker.tags is not None:
                tags += marker.tags
            value_str = f"""{{"{'", "'.join(set(tags))}"}}"""

            exist[index].tags = value_str

        await IdentificationMaker.bulk_update(exist, fields=["tags"])

    return IdentificationMarkerOut(
        count=len(identifications) + len(exist_ids),
        ids=[identification.id for identification in identifications] + exist_ids,
    )


@router.delete("/marker", response_model=IdentificationMarkerOut)
async def delete_marker(
    _: Annotated[User, Depends(is_admin)],
    data: IdentificationMarkerDelete,
) -> IdentificationMarkerOut:
    snapshot_ids = []
    if data.identifications_id is not None and len(data.identifications_id) > 0:
        identifications = (
            await Identification.filter(id__in=data.identifications_id)
            .all()
            .prefetch_related("snapshot")
        )
        if len(identifications) != len(data.identifications_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Some identifications id not found."
            )
        snapshot_ids += list(
            set([identification.snapshot.id for identification in identifications])
        )

    if data.snapshots_id is not None and len(data.snapshots_id) > 0:
        ids = await Snapshot.filter(id__in=data.snapshots_id).all().values_list("id", flat=True)
        if len(ids) != len(data.snapshots_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Some snapshots id not found."
            )
        snapshot_ids = list(set(snapshot_ids + ids))

    if len(snapshot_ids) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must send indetifications or snapshots ids",
        )

    print(snapshot_ids)
    identifications = await Identification.filter(snapshot_id__in=snapshot_ids).all()
    ids = [identification.id for identification in identifications]
    print(ids)
    print(identifications)

    conn = connections.get("default")
    query = f"""
    DELETE FROM "identification_marker"
    WHERE
      "identification_marker"."identification_id" IN ('{"', '".join([str(id) for id in ids])}')
    """
    await conn.execute_query(query)

    return IdentificationMarkerOut(count=len(ids), ids=ids)


@router.get("/aggregate")
async def get_aggregation(
    _: Annotated[User, Depends(is_admin)],
):
    query = """
    SELECT
      COUNT(label."value") AS total,
      label."value" AS label_value,
      "object"."name" AS object_name,
      snapshot.id AS snapshot_id,
      snapshot."timestamp" AS snapshot_timestamp,
      snapshot.public_url AS snapshot_url
    FROM
      user_identification
      INNER JOIN identification_marker ON identification_marker.identification_id = user_identification.identification_id
      LEFT JOIN identification ON identification.id = user_identification.identification_id
      LEFT JOIN snapshot ON snapshot.id = identification.snapshot_id
      LEFT JOIN label ON label.id = user_identification.label_id
      LEFT JOIN "object" ON label.object_id = "object".id
    GROUP BY
      label."value",
      "object"."name",
      snapshot.id,
      snapshot."timestamp",
      snapshot.public_url
    ORDER BY
      snapshot."timestamp" DESC
    """
    conn = connections.get("default")
    aggregation = await conn.execute_query_dict(query)
    snapshots_id = [identification["snapshot_id"] for identification in aggregation]
    ia_identifications = (
        await Identification.all()
        .filter(Q(snapshot_id__in=snapshots_id), ~Q(label__object__name="image_description"))
        .prefetch_related("snapshot", "label", "label__object")
    )

    out: dict[UUID, Aggregation] = {}
    for identification in aggregation:
        id: UUID = identification["snapshot_id"]
        human_identification = HumanIdentificationAggregation(
            object=identification["object_name"],
            label=identification["label_value"],
            count=identification["total"],
        )

        if id in out:
            out[id].human_identification.append(human_identification)
        else:
            out[id] = Aggregation(
                snapshot_id=id,
                snapshot_timestamp=identification["snapshot_timestamp"],
                snapshot_url=identification["snapshot_url"],
                ia_identification=[],
                human_identification=[human_identification],
            )
    for identification in ia_identifications:
        out[identification.snapshot.id].ia_identification.append(
            IaIdentificationAggregation(
                object=identification.label.object.name,
                label=identification.label.value,
            )
        )

    return list(out.values())
