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


class CameraIn(BaseModel):
    id: str
    name: Optional[str]
    rtsp_url: str
    update_interval: int
    latitude: float
    longitude: float


class CameraIdentificationOut(BaseModel):
    id: str
    name: Optional[str]
    rtsp_url: str
    update_interval: int
    latitude: float
    longitude: float
    objects: List[str]
    identifications: List["IdentificationOut"]


class CameraOut(BaseModel):
    id: str
    name: Optional[str]
    rtsp_url: str
    update_interval: int
    latitude: float
    longitude: float


class HeartbeatIn(BaseModel):
    healthy: bool


class HeartbeatOut(BaseModel):
    command: Optional[str]


class SnapshotOut(BaseModel):
    id: str
    camera_id: str
    image_url: str
    timestamp: datetime


class IdentificationOut(BaseModel):
    object: str
    title: str
    explanation: str
    timestamp: datetime
    label: str
    label_explanation: str
    snapshot: SnapshotOut


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
    title: str
    explanation: str


class ObjectOut(BaseModel):
    id: UUID
    name: str
    slug: str
    title: str
    explanation: str
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


class ObjectsSlugIn(BaseModel):
    objects: List[str]


class PromptsOut(BaseModel):
    prompts: List[PromptOut]


class PredictOut(BaseModel):
    error: bool
    message: Optional[str]


class Token(BaseModel):
    access_token: str
    token_type: str


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
CameraIdentificationOut.update_forward_refs()
IdentificationOut.update_forward_refs()
ObjectOut.update_forward_refs()
PromptOut.update_forward_refs()
SnapshotOut.update_forward_refs()
PredictOut.update_forward_refs()
UserInfo.update_forward_refs()
