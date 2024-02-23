# -*- coding: utf-8 -*-
from typing import Annotated
from uuid import UUID

from app.models import Agent
from app.oidc import get_current_user
from app.pydantic_models import OIDCUser, User
from app.utils import slugify
from fastapi import Depends, HTTPException, Security, status


async def get_user(user_info: Annotated[OIDCUser, Security(get_current_user, scopes=["profile"])]):
    if "vision-ai" not in user_info.groups:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You do not have access to this application.",
        )

    is_admin = "vision-ai-admin" in user_info.groups
    is_agent = "vision-ai-agent" in user_info.groups
    is_ai = "vision-ai-ai" in user_info.groups
    agent_id = UUID("00000000-0000-0000-0000-000000000000")

    if is_agent:
        agent = await Agent.get_or_none(auth_sub=user_info.sub)
        if agent is None:
            agent = await Agent.create(
                name=user_info.nickname,
                slug=slugify(user_info.nickname),
                auth_sub=user_info.sub,
            )

        agent_id = agent.id

    return User(
        agent_id=agent_id,
        name=user_info.nickname,
        is_admin=is_admin,
        is_agent=is_agent,
        is_ai=is_ai,
    )


async def is_admin(user: Annotated[User, Depends(get_user)]) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )

    return user


async def is_agent(user: Annotated[User, Depends(get_user)]) -> User:
    if not user.is_agent and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )

    return user


async def is_ai(user: Annotated[User, Depends(get_user)]) -> User:
    if not user.is_ai and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )

    return user


async def is_human(user: Annotated[User, Depends(get_user)]) -> User:
    if user.is_ai:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You don't have permission to do this.",
        )

    return user
