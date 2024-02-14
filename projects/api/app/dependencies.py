# -*- coding: utf-8 -*-
from typing import Annotated

from app.models import Agent
from app.oidc import get_current_user
from app.pydantic_models import AgentPydantic, APICaller, UserInfo
from app.utils import slugify
from fastapi import Depends, HTTPException, Security, status


async def get_caller(
    user_info: Annotated[UserInfo, Security(get_current_user, scopes=["profile"])]
):
    # If "vision-ai" not in groups, raise an exception.
    if "vision-ai" not in user_info.groups:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have access to this application.",
        )
    # If "vision-ai-admin" is in groups, it's an admin.
    is_admin = "vision-ai-admin" in user_info.groups
    # If "vision-ai-agent" is in groups, look for an agent with the same sub
    agent = None
    if "vision-ai-agent" in user_info.groups:
        agent_raw = await Agent.get_or_none(auth_sub=user_info.sub)
        if agent_raw is None:
            agent_raw = await Agent.create(
                name=user_info.nickname,
                slug=slugify(user_info.nickname),
                auth_sub=user_info.sub,
            )
        agent = AgentPydantic(
            id=agent_raw.id,
            name=agent_raw.name,
            slug=agent_raw.slug,
            auth_sub=agent_raw.auth_sub,
            last_heartbeat=agent_raw.last_heartbeat,
        )
    return APICaller(is_admin=is_admin, agent=agent)


async def is_admin(
    caller: Annotated[APICaller, Depends(get_caller)],
) -> None:
    if not caller.is_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )


async def is_agent(
    caller: Annotated[APICaller, Depends(get_caller)],
) -> AgentPydantic:
    if caller.agent is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )

    return caller.agent
