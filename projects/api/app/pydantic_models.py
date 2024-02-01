# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class AgentPydantic(BaseModel):
    id: UUID
    name: str
    slug: str
    auth_sub: str
    last_heartbeat: Optional[datetime]


class APICaller(BaseModel):
    is_admin: Optional[bool] = False
    agent: Optional[AgentPydantic]


class CameraConnectionInfo(BaseModel):
    id: str
    rtsp_url: str
    update_interval: int


class CameraIn(BaseModel):
    id: str
    name: Optional[str]
    rtsp_url: str
    update_interval: int
    latitude: float
    longitude: float


class CameraOut(BaseModel):
    id: str
    name: Optional[str]
    rtsp_url: str
    update_interval: int
    latitude: float
    longitude: float
    objects: List[str]
    identifications: List["IdentificationDetails"]


class Heartbeat(BaseModel):
    healthy: bool


class HeartbeatResponse(BaseModel):
    command: Optional[str]


class IdentificationDetails(BaseModel):
    object: str
    timestamp: Optional[datetime]
    label: Optional[str]


class LabelIn(BaseModel):
    value: str
    criteria: str
    identification_guide: str


class LabelOut(BaseModel):
    id: UUID
    value: str
    criteria: str
    identification_guide: str


class LabelUpdate(BaseModel):
    value: Optional[str]
    criteria: Optional[str]
    identification_guide: Optional[str]


class ObjectIn(BaseModel):
    name: str
    slug: str


class ObjectOut(BaseModel):
    id: UUID
    name: str
    slug: str
    labels: List[LabelOut]


class PromptIn(BaseModel):
    name: str
    model: str
    prompt_text: str
    max_output_token: int
    temperature: float
    top_k: int
    top_p: float


class PromptOut(BaseModel):
    id: UUID
    name: str
    model: str
    prompt_text: str
    max_output_token: int
    temperature: float
    top_k: int
    top_p: float
    objects: List[str]


class PromptsRequest(BaseModel):
    objects: List[str]


class PromptsResponse(BaseModel):
    prompts: List[PromptOut]


class Snapshot(BaseModel):
    camera_id: str
    image_url: str
    timestamp: datetime


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


AgentPydantic.update_forward_refs()
APICaller.update_forward_refs()
CameraConnectionInfo.update_forward_refs()
CameraOut.update_forward_refs()
IdentificationDetails.update_forward_refs()
ObjectOut.update_forward_refs()
PromptOut.update_forward_refs()
Snapshot.update_forward_refs()
SnapshotPostResponse.update_forward_refs()
UserInfo.update_forward_refs()
