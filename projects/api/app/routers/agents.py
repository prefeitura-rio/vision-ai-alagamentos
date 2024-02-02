# -*- coding: utf-8 -*-
from datetime import datetime
from functools import partial
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page
from fastapi_pagination.ext.tortoise import paginate as tortoise_paginate

from app.dependencies import get_caller, is_admin, is_agent
from app.models import Agent, Camera
from app.pydantic_models import (
    AgentPydantic,
    APICaller,
    CameraConnectionInfo,
    Heartbeat,
    HeartbeatResponse,
)
from app.utils import apply_to_list, transform_tortoise_to_pydantic

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("", response_model=Page[AgentPydantic])
async def get_agents(_=Depends(is_admin)) -> Page[AgentPydantic]:
    """Returns the list of registered agents."""
    return await tortoise_paginate(
        Agent,
        transformer=partial(
            apply_to_list,
            fn=partial(
                transform_tortoise_to_pydantic,
                pydantic_model=AgentPydantic,
                vars_map=[
                    ("id", "id"),
                    ("name", "name"),
                    ("slug", "slug"),
                    ("auth_sub", "auth_sub"),
                    ("last_heartbeat", "last_heartbeat"),
                ],
            ),
        ),
    )


@router.get("/me", response_model=AgentPydantic)
async def get_agent_me(agent=Depends(is_agent)) -> AgentPydantic:
    """Returns the agent informations."""
    return agent


@router.get("/cameras", response_model=Page[CameraConnectionInfo])
async def get_cameras(
    caller: Annotated[APICaller, Depends(get_caller)],
) -> Page[CameraConnectionInfo]:
    """Returns the list of cameras that the agent must get snapshots from."""
    if caller.is_admin:
        queryset = Camera
    elif caller.agent:
        queryset = Camera.filter(agents__id=caller.agent.id)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not allowed to list cameras",
        )
    return await tortoise_paginate(
        queryset,
        transformer=partial(
            apply_to_list,
            fn=partial(
                transform_tortoise_to_pydantic,
                pydantic_model=CameraConnectionInfo,
                vars_map=[
                    ("id", "id"),
                    ("rtsp_url", "rtsp_url"),
                    ("update_interval", "update_interval"),
                ],
            ),
        ),
    )


@router.get("/{agent_id}/cameras", response_model=Page[CameraConnectionInfo])
async def get_agent_cameras(
    agent_id: UUID,
    caller: Annotated[APICaller, Depends(get_caller)],
) -> Page[CameraConnectionInfo]:
    """Returns the list of cameras that the agent must get snapshots from."""
    # Caller must either be an admin or the agent itself. Also check for null agent.
    if not caller.is_admin and (not caller.agent or caller.agent.id != agent_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not allowed to list cameras for this agent.",
        )
    return await tortoise_paginate(
        Camera.filter(agents__id=agent_id),
        transformer=partial(
            apply_to_list,
            fn=partial(
                transform_tortoise_to_pydantic,
                pydantic_model=CameraConnectionInfo,
                vars_map=[
                    ("id", "id"),
                    ("rtsp_url", "rtsp_url"),
                    ("update_interval", "update_interval"),
                ],
            ),
        ),
    )


@router.post("/{agent_id}/cameras", response_model=CameraConnectionInfo)
async def add_camera_to_agent(
    agent_id: UUID,
    camera_id: str,
    _=Depends(is_admin),
) -> CameraConnectionInfo:
    """Adds a camera to an agent."""
    agent = await Agent.get_or_none(id=agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    camera = await Camera.get_or_none(id=camera_id)
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )
    await agent.cameras.add(camera)
    return CameraConnectionInfo(
        id=camera.id,
        rtsp_url=camera.rtsp_url,
        update_interval=camera.update_interval,
    )


@router.post("/{agent_id}/heartbeat", response_model=HeartbeatResponse)
async def agent_heartbeat(
    agent_id: UUID,
    heartbeat: Heartbeat,
    caller: Annotated[APICaller, Depends(get_caller)],
) -> HeartbeatResponse:
    """Endpoint for agents to send heartbeats to."""
    # Caller must be the agent itself.
    if not caller.agent or caller.agent.id != agent_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not allowed to send heartbeats for this agent.",
        )
    agent = await Agent.get(id=agent_id)
    if heartbeat.healthy:
        agent.last_heartbeat = datetime.now()
        await agent.save()
    return HeartbeatResponse(command="")  # TODO: Add commands
