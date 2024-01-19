# -*- coding: utf-8 -*-
from datetime import datetime

from app.models import Agent, Camera
from app.pydantic_models import CameraConnectionInfo, Heartbeat, HeartbeatResponse
from fastapi import APIRouter
from fastapi_pagination import Page, paginate

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("/{agent_id}/cameras", response_model=Page[CameraConnectionInfo])
async def get_agent_cameras(
    agent_id: int,
    # TODO: Add authentication
) -> Page[CameraConnectionInfo]:
    """Returns the list of cameras that the agent must get snapshots from."""
    cameras = await Camera.filter(agents__id=agent_id).all()
    cameras_connection_info = [
        CameraConnectionInfo(
            id=camera.id,
            rtsp_url=camera.rtsp_url,
            update_interval=camera.update_interval,
        )
        for camera in cameras
    ]
    return paginate(cameras_connection_info)


@router.post("/{agent_id}/heartbeat", response_model=HeartbeatResponse)
async def agent_heartbeat(
    agent_id: int,
    heartbeat: Heartbeat,
    # TODO: Add authentication
) -> HeartbeatResponse:
    """Endpoint for agents to send heartbeats to."""
    agent = await Agent.get(id=agent_id)
    if heartbeat.healthy:
        agent.last_heartbeat = datetime.now()
        await agent.save()
    return HeartbeatResponse(command="")  # TODO: Add commands
