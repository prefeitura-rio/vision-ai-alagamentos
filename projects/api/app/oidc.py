# -*- coding: utf-8 -*-
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from httpx import AsyncClient
from jose import jwt

from app import config
from app.pydantic_models import OIDCUser, Token

oidc_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


async def authenticate_user(form_data: OAuth2PasswordRequestForm) -> Token:
    async with AsyncClient() as client:
        response = await client.post(
            config.OIDC_TOKEN_URL,
            data={
                "grant_type": "password",
                "username": form_data.username,
                "password": form_data.password,
                "client_id": config.OIDC_CLIENT_ID,
                "client_secret": config.OIDC_CLIENT_SECRET,
                "scope": "profile",
            },
        )
        if response.status_code != 200:
            raise AuthError(response.json(), response.status_code)
        return Token(**response.json())


async def get_current_user(authorization_header: Annotated[str, Depends(oidc_scheme)]):
    try:
        unverified_header = jwt.get_unverified_header(authorization_header)
    except Exception:
        raise AuthError(
            {"code": "invalid_jwt_header", "description": "Unable to parse JWT header"},
            401,
        )

    rsa_key = {}
    algorithms = ""
    for key in config.JWS["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
            algorithms = key["alg"]

    if not rsa_key:
        raise AuthError(
            {
                "code": "invalid_rsa",
                "description": "Unable to find a valid RSA key.",
            },
            401,
        )

    try:
        payload = jwt.decode(
            authorization_header,
            rsa_key,
            algorithms=algorithms,
            audience=config.OIDC_CLIENT_ID,
            issuer=config.OIDC_ISSUER_URL,
        )
    except jwt.ExpiredSignatureError:
        raise AuthError({"code": "token_expired", "description": "token is expired"}, 401)
    except jwt.JWTClaimsError:
        raise AuthError(
            {
                "code": "invalid_claims",
                "description": "incorrect claims, please check the audience and issuer",
            },
            401,
        )
    except Exception:
        raise AuthError(
            {
                "code": "invalid_jwt",
                "description": "Unable to parse jwt token.",
            },
            401,
        )

    return OIDCUser(**payload)
