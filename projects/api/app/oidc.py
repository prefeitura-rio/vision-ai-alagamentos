# -*- coding: utf-8 -*-
import json
from typing import Annotated
from urllib.request import urlopen

from app import config
from app.pydantic_models import UserInfo
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import jwt

oidc_scheme = OAuth2PasswordBearer(
    tokenUrl=config.OIDC_TOKEN_URL,
    scopes={"openid": "openid", "email": "email", "profile": "profile"},
)


class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


async def get_current_user(authorization_header: Annotated[str, Depends(oidc_scheme)]):
    jwksurl = urlopen(config.OIDC_ISSUER_URL + "/jwks/")
    jwks = json.loads(jwksurl.read())

    try:
        unverified_header = jwt.get_unverified_header(authorization_header)
    except Exception:
        raise AuthError(
            {"code": "invalid_jwt_header", "description": "Unable to parse JWT header"},
            401,
        )

    rsa_key = {}
    algorithms = ""
    for key in jwks["keys"]:
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
        raise AuthError(
            {"code": "token_expired", "description": "token is expired"}, 401
        )
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

    return UserInfo(**payload)
