# -*- coding: utf-8 -*-
from datetime import datetime
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
from app.models import Agent, Camera, Identification, Label, Object
from app.pydantic_models import (
    APICaller,
    CameraIn,
    CameraOut,
    IdentificationOut,
    PredictOut,
    Snapshot,
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


class BigPage(Page[CameraOut]):
    __params_type__ = BigParams


router = APIRouter(prefix="/cameras", tags=["Cameras"])


@router.get("", response_model=BigPage)
async def get_cameras(params: BigParams = Depends(), _=Depends(is_admin)) -> Page[CameraOut]:
    """Get a list of all cameras."""
    cameras_out: Dict[str, CameraOut] = {}
    offset = params.size * (params.page - 1)

    ids = await Camera.all().limit(params.size).offset(offset).values_list("id", flat=True)

    cameras = await (
        Camera.filter(id__in=ids)
        .select_related(
            "identifications", "identifications__object__slug", "identifications__label__value"
        )
        .all()
        .values(
            "id",
            "name",
            "rtsp_url",
            "update_interval",
            "latitude",
            "longitude",
            "snapshot_url",
            "snapshot_timestamp",
            "identifications__id",
            "identifications__object__slug",
            "identifications__timestamp",
            "identifications__label__value",
            "identifications__label_explanation",
        )
    )

    for camera in cameras:
        id = camera["id"]
        slug = None
        identification_details = None
        if camera["identifications__id"] is not None:
            slug = camera["identifications__object__slug"]
            identification_details = IdentificationOut(
                object=slug,
                timestamp=camera["identifications__timestamp"],
                label=camera["identifications__label__value"],
                label_explanation=camera["identifications__label_explanation"],
            )

        if id in cameras_out:
            if identification_details is None:
                continue
            cameras_out[id].identifications.append(identification_details)
            if slug not in cameras_out[id].objects:
                cameras_out[id].objects.append(slug or "")
        else:
            cameras_out[id] = CameraOut(
                id=id,
                name=camera["name"],
                rtsp_url=camera["rtsp_url"],
                update_interval=camera["update_interval"],
                latitude=camera["latitude"],
                longitude=camera["longitude"],
                snapshot_url=camera["snapshot_url"],
                snapshot_timestamp=camera["snapshot_timestamp"],
                objects=[slug] if slug is not None else [],
                identifications=(
                    [identification_details] if identification_details is not None else []
                ),
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
        snapshot_url=camera.snapshot_url,
        snapshot_timestamp=camera.snapshot_timestamp,
        objects=[item.object.slug for item in await Identification.filter(camera=camera).all()],
        identifications=[
            IdentificationOut(
                object=item.object.slug,
                timestamp=item.timestamp,
                label=(await item.label).value if item.label else None,
                label_explanation=item.label_explanation,
            )
            for item in await Identification.filter(camera=camera).all()
        ],
    )


@router.get("/latest_snapshots", response_model=Page[Snapshot])
async def get_latest_snapshots(
    after: datetime,
    _: Annotated[APICaller, Depends(get_caller)],  # TODO: Review permissions here
) -> Page[Snapshot]:
    """Get snapshots after a treshold datetime."""
    return await tortoise_paginate(
        Camera.filter(snapshot_timestamp__gte=after),
        transformer=partial(
            apply_to_list,
            fn=partial(
                transform_tortoise_to_pydantic,
                pydantic_model=Snapshot,
                vars_map=[
                    ("id", "camera_id"),
                    ("snapshot_url", "image_url"),
                    ("snapshot_timestamp", "timestamp"),
                ],
            ),
        ),
    )


@router.get("/{camera_id}", response_model=CameraOut)
async def get_camera(
    camera_id: str,
    _: Annotated[APICaller, Depends(get_caller)],  # TODO: Review permissions here
) -> CameraOut:
    """Get information about a camera."""
    camera = await Camera.get(id=camera_id)
    camera_details = CameraOut(
        id=camera.id,
        name=camera.name,
        rtsp_url=camera.rtsp_url,
        update_interval=camera.update_interval,
        latitude=camera.latitude,
        longitude=camera.longitude,
        snapshot_url=camera.snapshot_url,
        snapshot_timestamp=camera.snapshot_timestamp,
        objects=[
            (await item.object).slug for item in await Identification.filter(camera=camera).all()
        ],
        identifications=[
            IdentificationOut(
                object=(await item.object).slug,
                timestamp=item.timestamp,
                label=(await item.label).value if item.label else None,
                label_explanation=item.label_explanation,
            )
            for item in await Identification.filter(camera=camera).all()
        ],
    )
    return camera_details


@router.get("/{camera_id}/snapshots", response_model=Snapshot)
async def get_camera_snapshot(
    camera_id: str,
    _: Annotated[APICaller, Depends(get_caller)],  # TODO: Review permissions here
) -> Snapshot:
    """Get a camera snapshot from the server."""
    camera = await Camera.get(id=camera_id)
    if not camera.snapshot_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera snapshot not found.",
        )
    return Snapshot(
        camera_id=camera.id, image_url=camera.snapshot_url, timestamp=camera.snapshot_timestamp
    )


@router.get("/{camera_id}/snapshots/identifications", response_model=List[IdentificationOut])
async def get_identifications(
    camera_id: str,
    _: Annotated[APICaller, Depends(get_caller)],  # TODO: Review permissions here
) -> List[IdentificationOut]:
    """Get all objects that the camera will identify."""
    camera = await Camera.get(id=camera_id)
    return [
        IdentificationOut(
            object=(await item.object).slug,
            timestamp=item.timestamp,
            label=(await item.label).value if item.label else None,
            label_explanation=item.label_explanation,
        )
        for item in await Identification.filter(camera=camera).all()
    ]


@router.post("/{camera_id}/snapshots/identifications", response_model=CameraOut)
async def create_identifcation(
    camera_id: str,
    identification_id: UUID,
    _=Depends(is_admin),
) -> CameraOut:
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
    return CameraOut(
        id=camera.id,
        name=camera.name,
        rtsp_url=camera.rtsp_url,
        update_interval=camera.update_interval,
        latitude=camera.latitude,
        longitude=camera.longitude,
        snapshot_url=camera.snapshot_url,
        snapshot_timestamp=camera.snapshot_timestamp,
        objects=[
            (await item.object).slug for item in await Identification.filter(camera=camera).all()
        ],
        identifications=[
            IdentificationOut(
                object=(await item.object).slug,
                timestamp=item.timestamp,
                label=(await item.label).value if item.label else None,
                label_explanation=item.label_explanation,
            )
            for item in await Identification.filter(camera=camera).all()
        ],
    )


@router.get(
    "/{camera_id}/snapshots/identifications/{identification_id}", response_model=IdentificationOut
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
    "/{camera_id}/snapshots/identifications/{identification_id}", response_model=IdentificationOut
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


@router.delete("/{camera_id}/snapshots/identifications/{identification_id}")
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


@router.post("/{camera_id}/snapshots/identifications/predict", response_model=PredictOut)
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
