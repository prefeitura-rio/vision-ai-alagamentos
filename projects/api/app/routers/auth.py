# -*- coding: utf-8 -*-
from typing import Annotated

from app.oidc import authenticate_user
from app.pydantic_models import Token
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    return await authenticate_user(form_data)
