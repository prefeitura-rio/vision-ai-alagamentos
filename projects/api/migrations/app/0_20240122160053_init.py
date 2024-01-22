# -*- coding: utf-8 -*-
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS "agent" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL UNIQUE,
    "slug" VARCHAR(255) NOT NULL UNIQUE,
    "last_heartbeat" TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS "camera" (
    "id" VARCHAR(30) NOT NULL  PRIMARY KEY,
    "name" VARCHAR(255),
    "rtsp_url" VARCHAR(255) NOT NULL UNIQUE,
    "update_interval" INT NOT NULL,
    "latitude" DOUBLE PRECISION NOT NULL,
    "longitude" DOUBLE PRECISION NOT NULL
);
CREATE TABLE IF NOT EXISTS "object" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL UNIQUE,
    "slug" VARCHAR(255) NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS "cameraidentification" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "timestamp" TIMESTAMPTZ NOT NULL,
    "label" BOOL NOT NULL,
    "camera_id" VARCHAR(30) NOT NULL REFERENCES "camera" ("id") ON DELETE CASCADE,
    "object_id" UUID NOT NULL REFERENCES "object" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "prompt" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL UNIQUE,
    "prompt_text" TEXT NOT NULL,
    "max_output_token" INT NOT NULL,
    "temperature" DOUBLE PRECISION NOT NULL,
    "top_k" INT NOT NULL,
    "top_p" DOUBLE PRECISION NOT NULL
);
CREATE TABLE IF NOT EXISTS "agent_camera" (
    "agent_id" UUID NOT NULL REFERENCES "agent" ("id") ON DELETE CASCADE,
    "camera_id" VARCHAR(30) NOT NULL REFERENCES "camera" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "prompt_object" (
    "prompt_id" UUID NOT NULL REFERENCES "prompt" ("id") ON DELETE CASCADE,
    "object_id" UUID NOT NULL REFERENCES "object" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
