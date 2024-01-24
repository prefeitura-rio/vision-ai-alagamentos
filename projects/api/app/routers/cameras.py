# -*- coding: utf-8 -*-
from app.models import Camera, CameraIdentification
from app.oidc import get_current_user
from app.pydantic_models import (
    CameraBasicInfo,
    CameraDetails,
    IdentificationDetails,
    Snapshot,
    SnapshotPostResponse,
    UserInfo,
)
from app.utils import (
    download_camera_snapshot_from_bucket,
    upload_camera_snapshot_to_bucket,
)
from fastapi import APIRouter, Security
from fastapi_pagination import Page, paginate

router = APIRouter(prefix="/cameras", tags=["Cameras"])


@router.get("", response_model=Page[CameraBasicInfo])
async def get_cameras(
    user: UserInfo = Security(get_current_user, scopes=["profile"]),
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
    user: UserInfo = Security(get_current_user, scopes=["profile"]),
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
    user: UserInfo = Security(get_current_user, scopes=["profile"]),
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
    user: UserInfo = Security(get_current_user, scopes=["profile"]),
) -> Snapshot:
    """Get a camera snapshot from the server."""
    camera = await Camera.get(id=camera_id)
    snapshot = await download_camera_snapshot_from_bucket(camera.id)
    return Snapshot(image_base64=snapshot)


@router.post("/{camera_id}/snapshot", response_model=SnapshotPostResponse)
async def camera_snapshot(
    camera_id: int,
    snapshot: Snapshot,
    user: UserInfo = Security(get_current_user, scopes=["profile"]),
) -> SnapshotPostResponse:
    """Post a camera snapshot to the server."""
    camera = await Camera.get(id=camera_id)
    await upload_camera_snapshot_to_bucket(
        image_base64=snapshot.image_base64, camera_id=camera.id
    )
    return SnapshotPostResponse(error=False, message="OK")
