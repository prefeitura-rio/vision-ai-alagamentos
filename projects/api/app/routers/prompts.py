# -*- coding: utf-8 -*-
from app.pydantic_models import PromptsRequest, PromptsResponse
from fastapi import APIRouter

router = APIRouter(prefix="/prompts", tags=["Prompts"])


@router.post("", response_model=PromptsResponse)
async def get_prompts(
    prompts_request: PromptsRequest,
    # TODO: Add authentication
) -> PromptsResponse:
    """
    Given a list of objects, returns the shortest list of prompts that covers all of the objects.
    """
    # TODO: Implement a functionality that, given the objects in the request, returns the shortest
    # list of prompts that covers all of the objects.
    raise NotImplementedError()
