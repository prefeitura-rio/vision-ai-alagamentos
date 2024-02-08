# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from functools import partial
from typing import Annotated, Dict, List
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi_pagination import Page, Params
from fastapi_pagination.api import create_page
from fastapi_pagination.ext.tortoise import paginate as tortoise_paginate
from nest_asyncio import os

from app import config
from app.dependencies import get_caller, is_admin
from app.models import Agent, Camera, Identification, Label, Object, Snapshot
from app.pydantic_models import (
    APICaller,
    CameraIdentificationOut,
    CameraIn,
    CameraOut,
    IdentificationOut,
    PredictOut,
    SnapshotOut,
)
from app.utils import (
    apply_to_list,
    generate_blob_path,
    get_prompt_formatted_text,
    get_prompts_best_fit,
    publish_message,
    transform_tortoise_to_pydantic,
    upload_file_to_bucket,
)


class BigParams(Params):
    size: int = Query(100, ge=1, le=3000)


class BigPage(Page[CameraIdentificationOut]):
    __params_type__ = BigParams


router = APIRouter(prefix="/cameras", tags=["Cameras"])


@router.get("", response_model=BigPage)
async def get_cameras(
    params: BigParams = Depends(), _=Depends(is_admin), hour_interval: int = 3
) -> Page[CameraIdentificationOut]:
    """Get a list of all cameras."""
    cameras_out: Dict[str, CameraIdentificationOut] = {}
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

    last3hour = datetime.now() - timedelta(hours=hour_interval)

    raw_identifications = (
        await Identification.all()
        .filter(snapshot__camera__id__in=ids, timestamp__gte=last3hour)
        .select_related(
            "snapshot",
            "snapshot__camera__id",
            "label",
            "label__object",
        )
        .values(
            "timestamp",
            "label_explanation",
            "snapshot__id",
            "snapshot__url",
            "snapshot__timestamp",
            "snapshot__camera__id",
            "label__value",
            "label__object__slug",
            "label__object__title",
            "label__object__explanation",
        )
    )

    for raw_identification in raw_identifications:
        id = raw_identification["snapshot__camera__id"]
        cameras_out[id].identifications.append(
            IdentificationOut(
                object=raw_identification["label__object__slug"],
                title=raw_identification["label__object__title"],
                explanation=raw_identification["label__object__explanation"],
                timestamp=raw_identification["timestamp"],
                label=raw_identification["label__value"],
                label_explanation=raw_identification["label_explanation"],
                snapshot=SnapshotOut(
                    id=str(raw_identification["snapshot__id"]),
                    camera_id=id,
                    image_url=raw_identification["snapshot__url"],
                    timestamp=raw_identification["snapshot__timestamp"],
                ),
            )
        )

    return create_page(list(cameras_out.values()), total=await Camera.all().count(), params=params)


@router.post("", response_model=CameraOut)
async def create_camera(camera_: CameraIn, _=Depends(is_admin)) -> CameraOut:
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
    _: Annotated[APICaller, Depends(get_caller)],  # TODO: Review permissions here
) -> CameraOut:
    """Get information about a camera."""
    raw_camera = await Camera.get_or_none(id=camera_id)
    if not raw_camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")

    camera = CameraOut(
        id=raw_camera.id,
        name=raw_camera.name,
        rtsp_url=raw_camera.rtsp_url,
        update_interval=raw_camera.update_interval,
        latitude=raw_camera.latitude,
        longitude=raw_camera.longitude,
    )

    return camera


@router.delete("/{camera_id}")
async def delete_camera(
    camera_id: str,
    _=Depends(is_admin),
) -> None:
    """Delete a camera."""
    camera = await Camera.get_or_none(id=camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")

    await Camera.filter(id=camera_id).delete()


@router.get("/latest_snapshots", response_model=Page[SnapshotOut])
async def get_latest_snapshots(
    after: datetime,
    _: Annotated[APICaller, Depends(get_caller)],  # TODO: Review permissions here
) -> Page[SnapshotOut]:
    """Get snapshots after a treshold datetime."""
    return await tortoise_paginate(
        Snapshot.filter(timestamp__gte=after),
        transformer=partial(
            apply_to_list,
            fn=partial(
                transform_tortoise_to_pydantic,
                pydantic_model=SnapshotOut,
                vars_map=[
                    ("id", "camera_id"),
                    ("snapshot_url", "image_url"),
                    ("snapshot_timestamp", "timestamp"),
                ],
            ),
        ),
    )


@router.get("/{camera_id}/snapshots", response_model=Page[SnapshotOut])
async def get_camera_snapshots(
    camera_id: str,
    _: Annotated[APICaller, Depends(get_caller)],  # TODO: Review permissions here
) -> Page[SnapshotOut]:
    """Get a camera snapshot from the server."""
    camera = await Camera.get(id=camera_id)
    return await tortoise_paginate(
        Snapshot.filter(camera=camera),
        transformer=partial(
            apply_to_list,
            fn=partial(
                transform_tortoise_to_pydantic,
                pydantic_model=SnapshotOut,
                vars_map=[
                    ("id", "camera_id"),
                    ("snapshot_url", "image_url"),
                    ("snapshot_timestamp", "timestamp"),
                ],
            ),
        ),
    )


@router.get("/{camera_id}/snapshots/identifications", response_model=List[IdentificationOut])
async def get_identifications(
    camera_id: str,
    _: Annotated[APICaller, Depends(get_caller)],  # TODO: Review permissions here
) -> List[IdentificationOut]:
    """Get all objects that the camera will identify."""
    # camera = await Camera.get(id=camera_id)
    return []


@router.post("/{camera_id}/snapshots/identifications", response_model=CameraIdentificationOut)
async def create_identifcation(
    camera_id: str,
    identification_id: UUID,
    _=Depends(is_admin),
) -> CameraIdentificationOut:
    """Add an snapshot identification to a camera."""
    camera = await Camera.get_or_none(id=camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")
    object_ = await Object.get_or_none(id=identification_id)
    if not object_:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found.")
    # Check if Identification already exists before adding
    if await Identification.get_or_none(camera=camera, object=object_):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Camera object already exists.",
        )
    await Identification.create(camera=camera, object=object_)
    return CameraIdentificationOut(
        id=camera.id,
        name=camera.name,
        rtsp_url=camera.rtsp_url,
        update_interval=camera.update_interval,
        latitude=camera.latitude,
        longitude=camera.longitude,
        objects=[(await item.object).slug for item in await camera.objects.all()],
        identifications=[],
    )


@router.get(
    "/{camera_id}/snapshots/{snapshot_id}/identifications", response_model=IdentificationOut
)
async def get_identification(
    camera_id: str,
    identification_id: UUID,
    _: Annotated[APICaller, Depends(get_caller)],  # TODO: Review permissions here
) -> IdentificationOut:
    """Get a camera snapshot identification."""
    camera = await Camera.get(id=camera_id)
    object_ = await Object.get(id=identification_id)
    identification = await Identification.get(camera=camera, object=object_)
    return IdentificationOut(
        object=(await identification.object).slug,
        timestamp=identification.timestamp,
        label=(await identification.label).value if identification.label else None,
        label_explanation=identification.label_explanation,
    )


@router.put(
    "/{camera_id}/snapshots/{snapshot_id}/identifications/{identification_id}",
    response_model=IdentificationOut,
)
async def update_identification(
    camera_id: str,
    identification_id: UUID,
    label: str,
    label_explanation: str,
    _=Depends(is_admin),  # TODO: Review permissions here
) -> IdentificationOut:
    """Update a camera snapshot identifications."""
    camera = await Camera.get_or_none(id=camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")
    object_ = await Object.get_or_none(id=identification_id)
    if not object_:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found.")
    identification = await Identification.get_or_none(camera=camera, object=object_)
    if not identification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera object not found.",
        )
    label_obj = await Label.get_or_none(object=object_, value=label)
    if not label_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Label not found.",
        )
    identification.label = label_obj
    identification.label_explanation = label_explanation
    identification.timestamp = datetime.now()
    await identification.save()
    return IdentificationOut(
        object=(await identification.object).slug,
        timestamp=identification.timestamp,
        label=(await identification.label).value if identification.label else None,
        label_explanation=identification.label_explanation,
    )


@router.delete("/{camera_id}/snapshots/{snapshot_id}/identifications/{identification_id}")
async def delete_identification(
    camera_id: str,
    identification_id: UUID,
    _=Depends(is_admin),
) -> None:
    """Delete a camera snapshot identification."""
    camera = await Camera.get_or_none(id=camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")
    object_ = await Object.get_or_none(id=identification_id)
    if not object_:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found.")
    await Identification.filter(camera=camera, object=object_).delete()


@router.post(
    "/{camera_id}/snapshots/{snapshot_id}/identifications/predict", response_model=PredictOut
)
async def predict(
    camera_id: str,
    file: Annotated[UploadFile, File(media_type="image/png")],
    caller: Annotated[APICaller, Depends(get_caller)],
) -> PredictOut:
    """Post a camera snapshot to the server."""
    # Caller must be an agent that has access to the camera.
    if not caller.agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not allowed to post snapshots for this camera.",
        )
    agent = await Agent.get_or_none(id=caller.agent.id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not allowed to post snapshots for this camera.",
        )
    if not agent.cameras.filter(id=camera_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not allowed to post snapshots for this camera.",
        )
    camera = await Camera.get(id=camera_id)
    tmp_fname = f"/tmp/{uuid4()}.png"
    blob_path = generate_blob_path(camera.id)

    with open(tmp_fname, "wb") as f:
        while contents := file.file.read(1024 * 1024):
            f.write(contents)

    blob = upload_file_to_bucket(
        bucket_name=config.GCS_BUCKET_NAME,
        file_path=tmp_fname,
        destination_blob_name=blob_path,
    )
    camera.snapshot_url = blob.public_url
    camera.snapshot_timestamp = datetime.now()
    await camera.save()

    os.remove(tmp_fname)

    print("END OF CAMERA SNAPSHOT POST")
    # Publish data to Pub/Sub
    camera_snapshot_ids = [
        str((await item.object).id) for item in await Identification.filter(camera=camera).all()
    ]
    camera_snpashot_slugs = [
        (await item.object).slug for item in await Identification.filter(camera=camera).all()
    ]
    print(f"camera_object_ids: {camera_snapshot_ids}")
    print(f"camera_object_slugs: {camera_snpashot_slugs}")

    if len(camera_snpashot_slugs):
        print("Start of Publishing to Pub/Sub")
        prompts = await get_prompts_best_fit(object_slugs=camera_snpashot_slugs)
        prompt = prompts[0]  # TODO: generalize this
        formatted_text = await get_prompt_formatted_text(
            prompt=prompt, object_slugs=camera_snpashot_slugs
        )
        message = {
            "camera_id": camera.id,
            "image_url": blob.public_url,
            "prompt_text": formatted_text,
            "object_ids": camera_snapshot_ids,
            "object_slugs": camera_snpashot_slugs,
            "model": prompt.model,
            "max_output_tokens": prompt.max_output_token,
            "temperature": prompt.temperature,
            "top_k": prompt.top_k,
            "top_p": prompt.top_p,
        }
        publish_message(data=message)
        print("End of Publishing to Pub/Sub")

    return PredictOut(error=False, message="OK")
