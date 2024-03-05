# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID, uuid4

from app import config
from app.dependencies import is_admin, is_agent, is_ai
from app.models import Agent, Camera, Identification, Label, Object, Snapshot
from app.pydantic_models import (
    CameraIdentificationOut,
    CameraIn,
    CameraOut,
    CameraUpdate,
    IdentificationOut,
    ObjectOut,
    PredictOut,
    SnapshotIn,
    SnapshotOut,
    User,
)
from app.utils import (
    get_gcp_credentials,
    get_prompt_formatted_text,
    get_prompts_best_fit,
    publish_message,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi_pagination import Page, Params
from fastapi_pagination.api import create_page
from google.cloud import storage
from tortoise.expressions import Q


class BigParams(Params):
    size: int = Query(100, ge=1, le=3000)


class BigPage(Page[CameraIdentificationOut]):
    __params_type__ = BigParams


router = APIRouter(prefix="/cameras", tags=["Cameras"])


@router.get("", response_model=BigPage)
async def get_cameras(
    _: Annotated[User, Depends(is_admin)], params: BigParams = Depends(), minute_interval: int = 30
) -> Page[CameraIdentificationOut]:
    """Get a list of all cameras."""
    cameras_out: dict[str, CameraIdentificationOut] = {}
    offset = params.size * (params.page - 1)

    ids = await Camera.all().limit(params.size).offset(offset).values_list("id", flat=True)

    cameras = (
        await Camera.all()
        .filter(id__in=ids)
        .select_related("objects")
        .values(
            "id",
            "name",
            "rtsp_url",
            "update_interval",
            "latitude",
            "longitude",
            "objects__slug",
        )
    )

    for camera in cameras:
        id = camera["id"]
        slug = camera["objects__slug"]

        if id in cameras_out:
            if slug is not None and slug not in cameras_out[id].objects:
                cameras_out[id].objects.append(slug)
        else:
            cameras_out[id] = CameraIdentificationOut(
                id=id,
                name=camera["name"],
                rtsp_url=camera["rtsp_url"],
                update_interval=camera["update_interval"],
                latitude=camera["latitude"],
                longitude=camera["longitude"],
                objects=[slug] if slug is not None else [],
                identifications=[],
            )

    lastminutes = datetime.now() - timedelta(minutes=minute_interval)

    identifications = (
        await Identification.all()
        .filter(snapshot__camera_id__in=ids, timestamp__gte=lastminutes)
        .prefetch_related(
            "snapshot",
            "snapshot__camera",
            "label",
            "label__object",
        )
        .order_by("-timestamp")
    )

    identifications_slug: dict[str, list[str]] = {}

    for identification in identifications:
        slug = identification.label.object.slug
        id = identification.snapshot.camera.id

        if id not in identifications_slug:
            identifications_slug[id] = []

        if slug in identifications_slug[id]:
            continue

        identifications_slug[id].append(slug)

        cameras_out[id].identifications.append(
            IdentificationOut(
                id=identification.id,
                object=slug,
                title=identification.label.object.title,
                question=identification.label.object.question,
                explanation=identification.label.object.explanation,
                timestamp=identification.timestamp,
                label=identification.label.value,
                label_text=identification.label.text,
                label_explanation=identification.label_explanation,
                snapshot=SnapshotOut(
                    id=identification.snapshot.id,
                    camera_id=id,
                    image_url=identification.snapshot.public_url,
                    timestamp=identification.snapshot.timestamp,
                ),
            )
        )

    return create_page(list(cameras_out.values()), total=await Camera.all().count(), params=params)


@router.post("", response_model=CameraOut)
async def create_camera(camera_: CameraIn, _: Annotated[User, Depends(is_admin)]) -> CameraOut:
    """Add a new camera."""
    camera = await Camera.create(**camera_.dict())
    return CameraOut(
        id=camera.id,
        name=camera.name,
        rtsp_url=camera.rtsp_url,
        update_interval=camera.update_interval,
        latitude=camera.latitude,
        longitude=camera.longitude,
    )


@router.get("/{camera_id}", response_model=CameraOut)
async def get_camera(
    camera_id: str,
    _: Annotated[User, Depends(is_agent)],
) -> CameraOut:
    """Get information about a camera."""
    camera = await Camera.get_or_none(id=camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")

    return CameraOut(
        id=camera.id,
        name=camera.name,
        rtsp_url=camera.rtsp_url,
        update_interval=camera.update_interval,
        latitude=camera.latitude,
        longitude=camera.longitude,
    )


@router.put("/{camera_id}", response_model=CameraOut)
async def update_camera(
    camera_id: str,
    camera_: CameraUpdate,
    _: Annotated[User, Depends(is_admin)],
) -> CameraOut:
    """Update a camera."""
    camera = await Camera.get_or_none(id=camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")

    await Camera.filter(id=camera_id).update(**camera_.dict(exclude_unset=True))
    return CameraOut(
        id=camera.id,
        name=camera.name,
        rtsp_url=camera.rtsp_url,
        update_interval=camera.update_interval,
        latitude=camera.latitude,
        longitude=camera.longitude,
    )


@router.delete("/{camera_id}")
async def delete_camera(
    camera_id: str,
    _: Annotated[User, Depends(is_admin)],
) -> None:
    """Delete a camera."""
    camera = await Camera.get_or_none(id=camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")

    await Camera.filter(id=camera_id).delete()


@router.get("/{camera_id}/objects", response_model=Page[ObjectOut])
async def get_camera_objects(
    camera_id: str,
    _: Annotated[User, Depends(is_agent)],
    params: Params = Depends(),
) -> Page[ObjectOut]:
    """Get a camera object from the server."""
    camera = await Camera.get_or_none(id=camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")

    objects = (
        await Object.filter(cameras__id=camera_id)
        .all()
        .limit(params.size)
        .offset(params.size * (params.page - 1))
    )
    objects_out = [
        ObjectOut(
            id=object.id,
            slug=object.slug,
            title=object.title,
            question=object.question,
            explanation=object.explanation,
        )
        for object in objects
    ]

    return create_page(
        objects_out, total=await Object.filter(cameras__id=camera_id).all().count(), params=params
    )


@router.get("/{camera_id}/snapshots", response_model=Page[SnapshotOut])
async def get_camera_snapshots(
    camera_id: str,
    _: Annotated[User, Depends(is_agent)],
    params: Params = Depends(),
    minute_interval: int = 30,
) -> Page[SnapshotOut]:
    """Get a camera snapshot from the server."""
    camera = await Camera.get_or_none(id=camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")

    lastminutes = datetime.now() - timedelta(minutes=minute_interval)
    filter_query = Snapshot.filter(
        Q(camera=camera) & (Q(timestamp__gte=lastminutes) | Q(timestamp__isnull=True))
    )
    snapshots = await filter_query.all().limit(params.size).offset(params.size * (params.page - 1))
    snapshots_out = [
        SnapshotOut(
            id=snapshot.id,
            camera_id=camera_id,
            image_url=snapshot.public_url,
            timestamp=snapshot.timestamp,
        )
        for snapshot in snapshots
    ]

    return create_page(snapshots_out, total=await filter_query.all().count(), params=params)


@router.post("/{camera_id}/snapshots", response_model=SnapshotOut)
async def create_camera_snapshot(
    camera_id: str,
    snapshot_in: SnapshotIn,
    user: Annotated[User, Depends(is_agent)],
) -> SnapshotOut:
    """Post a camera snapshot to the server."""
    camera = await Camera.get_or_none(id=camera_id, agents=user.agent_id)
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not allowed to post snapshots for this camera.",
        )

    id = uuid4()

    credentials = get_gcp_credentials()
    storage_client = storage.Client(credentials=credentials)
    bucket = storage_client.bucket(config.GCS_BUCKET_NAME)
    path_data = datetime.now().strftime("ano=%Y/mes=%m/dia=%d")
    blob_path = f"{config.GCS_BUCKET_PATH_PREFIX}/{path_data}/camera_id={camera_id}/{id}.png"
    blob = bucket.blob(blob_name=blob_path)
    url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=15),
        method="PUT",
        content_md5=snapshot_in.hash_md5,
        content_type="image/png",
    )

    snapshot = await Snapshot.create(
        id=id,
        camera=camera,
        public_url=blob.public_url,
        timestamp=None,
    )

    return SnapshotOut(
        id=snapshot.id,
        camera_id=camera_id,
        image_url=url,
        timestamp=snapshot.timestamp,
    )


@router.post("/{camera_id}/snapshots/{snapshot_id}/predict", response_model=PredictOut)
async def predict(
    camera_id: str,
    snapshot_id: str,
    user: Annotated[User, Depends(is_agent)],
) -> PredictOut:
    """Post a camera snapshot to the server."""
    agent = await Agent.get_or_none(id=user.agent_id, cameras__id=camera_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not allowed to post snapshots for this camera.",
        )

    snapshot = await Snapshot.get_or_none(id=snapshot_id, camera_id=camera_id)
    if not snapshot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

    snapshot.timestamp = datetime.now()
    await snapshot.save()

    objects = await Object.filter(cameras__id=camera_id).all()

    # Publish data to Pub/Sub
    camera_snapshot_ids = [item.id for item in objects]
    camera_snapshot_slugs = [item.slug for item in objects]

    if len(camera_snapshot_slugs):
        prompts = await get_prompts_best_fit(objects=objects, one=True)
        if len(prompts) == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompts not found")

        prompt = prompts[0]  # TODO: generalize this
        formatted_text = await get_prompt_formatted_text(prompt=prompt, objects=objects)
        message = {
            "camera_id": camera_id,
            "snapshot_id": snapshot.id,
            "image_url": snapshot.public_url,
            "prompt_text": formatted_text,
            "object_ids": camera_snapshot_ids,
            "object_slugs": camera_snapshot_slugs,
            "model": prompt.model,
            "max_output_tokens": prompt.max_output_token,
            "temperature": prompt.temperature,
            "top_k": prompt.top_k,
            "top_p": prompt.top_p,
        }
        publish_message(data=message)

    return PredictOut(error=False, message="OK")


@router.get(
    "/{camera_id}/snapshots/{snapshot_id}/identifications", response_model=IdentificationOut
)
async def get_identification(
    camera_id: str,
    snapshot_id: UUID,
    _: Annotated[User, Depends(is_agent)],
) -> list[IdentificationOut]:
    """Get a camera snapshot identification."""
    camera = await Camera.get_or_none(id=camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")
    snapshot = await Snapshot.get_or_none(id=snapshot_id, camera=camera)
    if not snapshot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found.")

    identifications = (
        await Identification.all()
        .filter(snapshot=snapshot)
        .prefetch_related("label", "label__object")
    )

    identifications = [
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
                id=snapshot.id,
                camera_id=camera.id,
                image_url=snapshot.public_url,
                timestamp=snapshot.timestamp,
            ),
        )
        for identification in identifications
    ]

    return JSONResponse(content=jsonable_encoder(identifications))  # noqa


@router.post(
    "/{camera_id}/snapshots/{snapshot_id}/identifications",
    response_model=IdentificationOut,
)
async def create_identification(
    camera_id: str,
    snapshot_id: UUID,
    object_id: UUID,
    label_value: str,
    label_explanation: str,
    _: Annotated[User, Depends(is_ai)],
) -> IdentificationOut:
    """Update a camera snapshot identifications."""
    snapshot = await Snapshot.get_or_none(id=snapshot_id, camera_id=camera_id)
    if not snapshot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found.")
    label = await Label.get_or_none(object_id=object_id, value=label_value).prefetch_related(
        "object"
    )
    if not label:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Label not found.")

    object_ = await label.object.get(id=object_id)

    identification = await Identification.create(
        snapshot=snapshot,
        label=label,
        timestamp=datetime.now(),
        label_explanation=label_explanation,
    )

    return IdentificationOut(
        id=identification.id,
        object=object_.slug,
        title=object_.title,
        question=object_.question,
        explanation=object_.explanation,
        timestamp=identification.timestamp,
        label=label.value,
        label_text=label.text,
        label_explanation=identification.label_explanation,
        snapshot=SnapshotOut(
            id=snapshot.id,
            camera_id=camera_id,
            image_url=snapshot.public_url,
            timestamp=snapshot.timestamp,
        ),
    )


@router.delete("/{camera_id}/snapshots/{snapshot_id}/identifications/{identification_id}")
async def delete_identification(
    camera_id: str,
    snapshot_id: UUID,
    identification_id: UUID,
    _: Annotated[User, Depends(is_admin)],
) -> None:
    """Delete a camera snapshot identification."""
    camera = await Camera.get_or_none(id=camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")
    snapshot = await Snapshot.get_or_none(id=snapshot_id, camera=camera)
    if not snapshot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found.")
    await Identification.filter(id=identification_id, snapshot=snapshot).delete()
