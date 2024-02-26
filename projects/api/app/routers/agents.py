# -*- coding: utf-8 -*-
from datetime import datetime
from functools import partial
from typing import Annotated
from uuid import UUID

from app.dependencies import get_user, is_admin, is_agent
from app.models import Agent, Camera
from app.pydantic_models import AgentOut, CameraOut, HeartbeatIn, HeartbeatOut, User
from app.utils import apply_to_list, transform_tortoise_to_pydantic
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page
from fastapi_pagination.ext.tortoise import paginate as tortoise_paginate

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("", response_model=Page[AgentOut])
async def get_agents(_: Annotated[User, Depends(is_admin)]) -> Page[AgentOut]:
    """Returns the list of registered agents."""
    return await tortoise_paginate(
        Agent,
        transformer=partial(
            apply_to_list,
            fn=partial(
                transform_tortoise_to_pydantic,
                pydantic_model=AgentOut,
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


@router.get("/me", response_model=AgentOut)
async def get_agent_me(user: Annotated[User, Depends(is_agent)]) -> AgentOut:
    """Returns the agent informations."""
    agent = await Agent.get(id=user.agent_id)

    return AgentOut(
        id=agent.id,
        name=agent.name,
        slug=agent.slug,
        auth_sub=agent.auth_sub,
        last_heartbeat=agent.last_heartbeat,
    )


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: UUID, _: Annotated[User, Depends(is_admin)]) -> AgentOut:
    """Returns the agent informations."""
    agent = await Agent.get(id=agent_id)

    return AgentOut(
        id=agent.id,
        name=agent.name,
        slug=agent.slug,
        auth_sub=agent.auth_sub,
        last_heartbeat=agent.last_heartbeat,
    )


@router.get("/cameras", response_model=Page[CameraOut])
async def get_cameras(
    user: Annotated[User, Depends(get_user)],
) -> Page[CameraOut]:
    """Returns the list of cameras that the agent must get snapshots from."""
    if user.is_admin:
        queryset = Camera
    elif user.is_agent:
        queryset = Camera.filter(agents__id=user.agent_id)
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
                pydantic_model=CameraOut,
                vars_map=[
                    ("id", "id"),
                    ("name", "name"),
                    ("rtsp_url", "rtsp_url"),
                    ("update_interval", "update_interval"),
                    ("latitude", "latitude"),
                    ("longitude", "longitude"),
                ],
            ),
        ),
    )


@router.get("/{agent_id}/cameras", response_model=Page[CameraOut])
async def get_agent_cameras(
    agent_id: UUID,
    user: Annotated[User, Depends(get_user)],
) -> Page[CameraOut]:
    """Returns the list of cameras that the agent must get snapshots from."""
    # user must either be an admin or the agent itself.
    if not user.is_admin and (not user.is_agent or user.agent_id != agent_id):
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
                pydantic_model=CameraOut,
                vars_map=[
                    ("id", "id"),
                    ("name", "name"),
                    ("rtsp_url", "rtsp_url"),
                    ("update_interval", "update_interval"),
                    ("latitude", "latitude"),
                    ("longitude", "longitude"),
                ],
            ),
        ),
    )


@router.post("/{agent_id}/heartbeat", response_model=HeartbeatOut)
async def agent_heartbeat(
    agent_id: UUID,
    heartbeat: HeartbeatIn,
    user: Annotated[User, Depends(is_agent)],
) -> HeartbeatOut:
    """Endpoint for agents to send heartbeats to."""
    # user must be the agent itself.
    if not user.is_agent or user.agent_id != agent_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not allowed to send heartbeats for this agent.",
        )
    agent = await Agent.get(id=agent_id)
    if heartbeat.healthy:
        agent.last_heartbeat = datetime.now()
        await agent.save()
    return HeartbeatOut(command="")  # TODO: Add commands


@router.post("/{agent_id}/cameras/{camera_id}", response_model=CameraOut)
async def add_camera_to_agent(
    agent_id: UUID,
    camera_id: str,
    _: Annotated[User, Depends(is_admin)],
) -> CameraOut:
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
    return CameraOut(
        id=camera.id,
        name=camera.name,
        rtsp_url=camera.rtsp_url,
        update_interval=camera.update_interval,
        latitude=camera.latitude,
        longitude=camera.longitude,
    )


@router.delete("/{agent_id}/cameras/{camera_id}", response_model=CameraOut)
async def remove_camera_from_agent(
    agent_id: UUID,
    camera_id: str,
    _: Annotated[User, Depends(is_admin)],
) -> CameraOut:
    """Removes a camera from an agent."""
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
    await agent.cameras.remove(camera)
    return CameraOut(
        id=camera.id,
        name=camera.name,
        rtsp_url=camera.rtsp_url,
        update_interval=camera.update_interval,
        latitude=camera.latitude,
        longitude=camera.longitude,
    )
