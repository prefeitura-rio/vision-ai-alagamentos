# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class CameraBasicInfo(BaseModel):
    id: str
    latitude: float
    longitude: float
    objects: List[str]


class CameraConnectionInfo(BaseModel):
    id: str
    rtsp_url: str
    update_interval: int


class CameraDetails(BaseModel):
    id: str
    latitude: float
    longitude: float
    objects: List[str]
    identifications: List["IdentificationDetails"]


class IdentificationDetails(BaseModel):
    object: str
    timestamp: datetime
    label: bool


class Heartbeat(BaseModel):
    healthy: bool


class HeartbeatResponse(BaseModel):
    command: Optional[str]


class PromptObjects(BaseModel):
    prompt: str
    objects: List[str]


class PromptsRequest(BaseModel):
    objects: List[str]


class PromptsResponse(BaseModel):
    prompts: List[PromptObjects]


class Snapshot(BaseModel):
    image_base64: str


class SnapshotPostResponse(BaseModel):
    error: bool
    message: Optional[str]


class UserInfo(BaseModel):
    iss: str
    sub: str
    aud: str
    exp: int
    iat: int
    auth_time: int
    acr: str
    azp: str
    uid: str
    email: Optional[str]
    email_verified: Optional[bool]
    name: Optional[str]
    given_name: Optional[str]
    preferred_username: Optional[str]
    nickname: Optional[str]
    groups: Optional[List[str]]


CameraBasicInfo.update_forward_refs()
CameraConnectionInfo.update_forward_refs()
CameraDetails.update_forward_refs()
IdentificationDetails.update_forward_refs()
HeartbeatResponse.update_forward_refs()
PromptObjects.update_forward_refs()
PromptsRequest.update_forward_refs()
PromptsResponse.update_forward_refs()
Snapshot.update_forward_refs()
SnapshotPostResponse.update_forward_refs()
UserInfo.update_forward_refs()
