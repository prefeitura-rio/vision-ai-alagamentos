# -*- coding: utf-8 -*-
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class User(BaseModel):
    agent_id: UUID
    name: str
    is_admin: bool
    is_agent: bool
    is_ai: bool


class AgentOut(BaseModel):
    id: UUID
    name: str
    slug: str
    auth_sub: str
    last_heartbeat: datetime | None


class CameraIn(BaseModel):
    id: str
    name: str | None
    rtsp_url: str
    update_interval: int
    latitude: float
    longitude: float


class CameraIdentificationOut(BaseModel):
    id: str
    name: str | None
    rtsp_url: str
    update_interval: int
    latitude: float
    longitude: float
    objects: list[str]
    identifications: list["IdentificationOut"]


class CameraOut(BaseModel):
    id: str
    name: str | None
    rtsp_url: str
    update_interval: int
    latitude: float
    longitude: float


class CameraUpdate(BaseModel):
    name: str | None
    rtsp_url: str | None
    update_interval: int | None
    latitude: float | None
    longitude: float | None


class HeartbeatIn(BaseModel):
    healthy: bool


class HeartbeatOut(BaseModel):
    command: str | None


class SnapshotIn(BaseModel):
    hash_md5: str
    content_length: int


class SnapshotOut(BaseModel):
    id: UUID
    camera_id: str
    image_url: str
    timestamp: datetime | None


class IdentificationOut(BaseModel):
    id: UUID
    object: str
    title: str | None
    question: str | None
    explanation: str | None
    timestamp: datetime
    label: str
    label_text: str
    label_explanation: str
    snapshot: SnapshotOut


class IdentificationHumanIN(BaseModel):
    identification_id: UUID
    label: str


class IdentificationMarkerIn(BaseModel):
    identifications_id: list[UUID] | None
    snapshots_id: list[UUID] | None
    tags: list[str] | None


class IdentificationMarkerDelete(BaseModel):
    identifications_id: list[UUID] | None
    snapshots_id: list[UUID] | None


class IdentificationMarkerOut(BaseModel):
    count: int
    ids: list[UUID]


class LabelIn(BaseModel):
    value: str
    text: str
    criteria: str
    identification_guide: str


class LabelsIn(BaseModel):
    labels: list[str]


class LabelOut(BaseModel):
    id: UUID
    value: str
    text: str
    criteria: str
    identification_guide: str


class LabelUpdate(BaseModel):
    value: str | None
    text: str | None
    criteria: str | None
    identification_guide: str | None


class ObjectIn(BaseModel):
    name: str
    slug: str
    title: str
    question: str
    explanation: str


class ObjectOut(BaseModel):
    id: UUID
    name: str
    slug: str
    title: str | None
    question: str | None
    explanation: str | None
    labels: list[LabelOut]


class ObjectUpdate(BaseModel):
    name: str | None
    slug: str | None
    title: str | None
    question: str | None
    explanation: str | None


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
    objects: list[str]


class ObjectsSlugIn(BaseModel):
    objects: list[str]


class PromptsOut(BaseModel):
    prompts: list[PromptOut]


class PredictOut(BaseModel):
    error: bool
    message: str | None


class IaIdentificationAggregation(BaseModel):
    object: str
    label: str


class HumanIdentificationAggregation(BaseModel):
    object: str
    label: str
    count: int


class Aggregation(BaseModel):
    snapshot_id: UUID
    snapshot_timestamp: datetime
    snapshot_url: str
    ia_identification: list[IaIdentificationAggregation]
    human_identification: list[HumanIdentificationAggregation]


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class OIDCUser(BaseModel):
    iss: str
    sub: str
    aud: str
    exp: int
    iat: int
    auth_time: int
    acr: str
    azp: str
    uid: str
    email: str | None
    email_verified: bool | None
    name: str | None
    given_name: str | None
    preferred_username: str | None
    nickname: str
    groups: list[str]


User.update_forward_refs()
AgentOut.update_forward_refs()
CameraIdentificationOut.update_forward_refs()
IdentificationOut.update_forward_refs()
ObjectOut.update_forward_refs()
PromptOut.update_forward_refs()
SnapshotOut.update_forward_refs()
PredictOut.update_forward_refs()
OIDCUser.update_forward_refs()
