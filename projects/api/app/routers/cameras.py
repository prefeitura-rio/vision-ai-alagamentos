# -*- coding: utf-8 -*-
from app.models import Camera, CameraIdentification
from app.pydantic_models import (
    CameraBasicInfo,
    CameraDetails,
    IdentificationDetails,
    Snapshot,
    SnapshotPostResponse,
)
from fastapi import APIRouter
from fastapi_pagination import Page, paginate

router = APIRouter(prefix="/cameras", tags=["Cameras"])


@router.get("", response_model=Page[CameraBasicInfo])
async def get_cameras(
    # TODO: Add authentication
) -> Page[CameraBasicInfo]:
    """Get a list of basic information about all cameras."""
    cameras = await Camera.all()
    cameras_basic_info = [
        CameraBasicInfo(
            id=camera.id,
            latitude=camera.latitude,
            longitude=camera.longitude,
            objects=[
                item.object.slug
                for item in await CameraIdentification.filter(camera=camera).all()
            ],
        )
        for camera in cameras
    ]
    return paginate(cameras_basic_info)


@router.get("/details", response_model=Page[CameraDetails])
async def get_cameras_details(
    # TODO: Add authentication
) -> Page[CameraDetails]:
    """Get a list of detailed information about all cameras."""
    cameras = await Camera.all()
    cameras_details = [
        CameraDetails(
            id=camera.id,
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
        for camera in cameras
    ]
    return paginate(cameras_details)


@router.get("/{camera_id}/details", response_model=CameraDetails)
async def get_camera_details(
    camera_id: int,
    # TODO: Add authentication
) -> CameraDetails:
    """Get detailed information about a camera."""
    camera = await Camera.get(id=camera_id)
    camera_details = CameraDetails(
        id=camera.id,
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
    return camera_details


@router.get("/{camera_id}/snapshot", response_model=Snapshot)
async def get_camera_snapshot(
    camera_id: int,
    # TODO: Add authentication
) -> Snapshot:
    """Get a camera snapshot from the server."""
    raise NotImplementedError()  # TODO: Implement


@router.post("/{camera_id}/snapshot", response_model=SnapshotPostResponse)
async def camera_snapshot(
    camera_id: int,
    snapshot: Snapshot,
    # TODO: Add authentication
) -> SnapshotPostResponse:
    """Post a camera snapshot to the server."""
    raise NotImplementedError()  # TODO: Implement
