# -*- coding: utf-8 -*-
from datetime import datetime
from functools import partial
from typing import Annotated, List
from uuid import UUID

from app.dependencies import get_caller, is_admin
from app.models import Agent, Camera, CameraIdentification, Object
from app.pydantic_models import (
    APICaller,
    CameraIn,
    CameraOut,
    IdentificationDetails,
    Snapshot,
    SnapshotPostResponse,
)
from app.utils import (
    apply_to_list,
    download_camera_snapshot_from_bucket,
    transform_tortoise_to_pydantic,
    upload_camera_snapshot_to_bucket,
)
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page
from fastapi_pagination.ext.tortoise import paginate as tortoise_paginate
from tortoise.fields import ReverseRelation

router = APIRouter(prefix="/cameras", tags=["Cameras"])


@router.get("", response_model=Page[CameraOut])
async def get_cameras(_=Depends(is_admin)) -> Page[CameraOut]:
    """Get a list of all cameras."""

    async def get_objects(identifications_relation: ReverseRelation) -> List[str]:
        identifications: List[
            CameraIdentification
        ] = await identifications_relation.all()
        return [(await item.object).slug for item in identifications]

    async def get_identifications(
        identifications_relation: ReverseRelation,
    ) -> List[IdentificationDetails]:
        identifications: List[
            CameraIdentification
        ] = await identifications_relation.all()
        return [
            IdentificationDetails(
                object=(await item.object).slug,
                timestamp=item.timestamp,
                label=item.label,
            )
            for item in identifications
        ]

    return await tortoise_paginate(
        Camera,
        transformer=partial(
            apply_to_list,
            fn=partial(
                transform_tortoise_to_pydantic,
                pydantic_model=CameraOut,
                vars_map=[
                    ("id", "id"),
                    ("name", "name"),
                    ("rtsp_url", "rtsp_url"),
                    ("update_interval", "update_interval"),
                    ("latitude", "latitude"),
                    ("longitude", "longitude"),
                    ("identifications", ("objects", get_objects)),
                    ("identifications", ("identifications", get_identifications)),
                ],
            ),
        ),
    )


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
        objects=[
            item.object.slug
            for item in await CameraIdentification.filter(camera=camera).all()
        ],
        identifications=[
            IdentificationDetails(
                object=item.object.slug, timestamp=item.timestamp, label=item.label
            )
            for item in await CameraIdentification.filter(camera=camera).all()
        ],
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
        objects=[
            (await item.object).slug
            for item in await CameraIdentification.filter(camera=camera).all()
        ],
        identifications=[
            IdentificationDetails(
                object=(await item.object).slug,
                timestamp=item.timestamp,
                label=item.label,
            )
            for item in await CameraIdentification.filter(camera=camera).all()
        ],
    )
    return camera_details


@router.get("/{camera_id}/objects", response_model=List[IdentificationDetails])
async def get_camera_objects(
    camera_id: str,
    _: Annotated[APICaller, Depends(get_caller)],  # TODO: Review permissions here
) -> List[IdentificationDetails]:
    """Get all objects that the camera will identify."""
    camera = await Camera.get(id=camera_id)
    return [
        IdentificationDetails(
            object=(await item.object).slug, timestamp=item.timestamp, label=item.label
        )
        for item in await CameraIdentification.filter(camera=camera).all()
    ]


@router.post("/{camera_id}/objects", response_model=CameraOut)
async def create_camera_object(
    camera_id: str,
    object_id: UUID,
    _=Depends(is_admin),
) -> CameraOut:
    """Add an object to a camera."""
    camera = await Camera.get_or_none(id=camera_id)
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found."
        )
    object_ = await Object.get_or_none(id=object_id)
    if not object_:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Object not found."
        )
    await CameraIdentification.create(camera=camera, object=object_)
    # TODO: check if CameraIdentification already exists before adding
    return CameraOut(
        id=camera.id,
        name=camera.name,
        rtsp_url=camera.rtsp_url,
        update_interval=camera.update_interval,
        latitude=camera.latitude,
        longitude=camera.longitude,
        objects=[
            (await item.object).slug
            for item in await CameraIdentification.filter(camera=camera).all()
        ],
        identifications=[
            IdentificationDetails(
                object=(await item.object).slug,
                timestamp=item.timestamp,
                label=item.label,
            )
            for item in await CameraIdentification.filter(camera=camera).all()
        ],
    )


@router.get("/{camera_id}/objects/{object_id}", response_model=IdentificationDetails)
async def get_camera_object(
    camera_id: str,
    object_id: UUID,
    _: Annotated[APICaller, Depends(get_caller)],  # TODO: Review permissions here
) -> IdentificationDetails:
    """Get a camera object."""
    camera = await Camera.get(id=camera_id)
    object_ = await Object.get(id=object_id)
    identification = await CameraIdentification.get(camera=camera, object=object_)
    return IdentificationDetails(
        object=(await identification.object).slug,
        timestamp=identification.timestamp,
        label=identification.label,
    )


@router.put("/{camera_id}/objects/{object_id}", response_model=IdentificationDetails)
async def update_camera_object(
    camera_id: str,
    object_id: UUID,
    label: bool,
    _=Depends(is_admin),  # TODO: Review permissions here
) -> IdentificationDetails:
    """Update a camera object."""
    camera = await Camera.get_or_none(id=camera_id)
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found."
        )
    object_ = await Object.get_or_none(id=object_id)
    if not object_:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Object not found."
        )
    identification = await CameraIdentification.get_or_none(
        camera=camera, object=object_
    )
    if not identification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera object not found.",
        )
    identification.label = label
    identification.timestamp = datetime.now()
    await identification.save()
    return IdentificationDetails(
        object=(await identification.object).slug,
        timestamp=identification.timestamp,
        label=identification.label,
    )


@router.delete("/{camera_id}/objects/{object_id}")
async def delete_camera_object(
    camera_id: str,
    object_id: UUID,
    _=Depends(is_admin),
) -> None:
    """Delete a camera object."""
    camera = await Camera.get_or_none(id=camera_id)
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found."
        )
    object_ = await Object.get_or_none(id=object_id)
    if not object_:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Object not found."
        )
    await CameraIdentification.filter(camera=camera, object=object_).delete()


@router.get("/{camera_id}/snapshot", response_model=Snapshot)
async def get_camera_snapshot(
    camera_id: str,
    _: Annotated[APICaller, Depends(get_caller)],  # TODO: Review permissions here
) -> Snapshot:
    """Get a camera snapshot from the server."""
    camera = await Camera.get(id=camera_id)
    # TODO: Modify download for no-base64
    snapshot = download_camera_snapshot_from_bucket(camera_id=camera.id)
    return Snapshot(image_base64=snapshot)


@router.post("/{camera_id}/snapshot", response_model=SnapshotPostResponse)
async def camera_snapshot(
    camera_id: str,
    snapshot: Snapshot,
    caller: Annotated[APICaller, Depends(get_caller)],
) -> SnapshotPostResponse:
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
    upload_camera_snapshot_to_bucket(  # TODO: Modify upload for no-base64
        image_base64=snapshot.image_base64, camera_id=camera.id
    )
    return SnapshotPostResponse(error=False, message="OK")
