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
    "auth_sub" VARCHAR(255) NOT NULL UNIQUE,
    "last_heartbeat" TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS "idx_agent_auth_su_ec014c" ON "agent" ("auth_sub");
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
    "slug" VARCHAR(255) NOT NULL UNIQUE,
    "title" VARCHAR(255) NOT NULL UNIQUE,
    "explanation" TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS "label" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "value" VARCHAR(255) NOT NULL,
    "criteria" TEXT NOT NULL,
    "identification_guide" TEXT NOT NULL,
    "object_id" UUID NOT NULL REFERENCES "object" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_label_object__5c5639" UNIQUE ("object_id", "value")
);
CREATE TABLE IF NOT EXISTS "prompt" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL UNIQUE,
    "model" VARCHAR(255) NOT NULL,
    "prompt_text" TEXT NOT NULL,
    "max_output_token" INT NOT NULL,
    "temperature" DOUBLE PRECISION NOT NULL,
    "top_k" INT NOT NULL,
    "top_p" DOUBLE PRECISION NOT NULL
);
CREATE TABLE IF NOT EXISTS "snapshot" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "url" VARCHAR(255) NOT NULL,
    "timestamp" TIMESTAMPTZ NOT NULL,
    "camera_id" VARCHAR(30) NOT NULL REFERENCES "camera" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "identification" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "timestamp" TIMESTAMPTZ,
    "label_explanation" TEXT,
    "label_id" UUID NOT NULL REFERENCES "label" ("id") ON DELETE CASCADE,
    "snapshot_id" UUID NOT NULL REFERENCES "snapshot" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "agent_camera" (
    "agent_id" UUID NOT NULL REFERENCES "agent" ("id") ON DELETE CASCADE,
    "camera_id" VARCHAR(30) NOT NULL REFERENCES "camera" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "camera_object" (
    "camera_id" VARCHAR(30) NOT NULL REFERENCES "camera" ("id") ON DELETE CASCADE,
    "object_id" UUID NOT NULL REFERENCES "object" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "prompt_object" (
    "prompt_id" UUID NOT NULL REFERENCES "prompt" ("id") ON DELETE CASCADE,
    "object_id" UUID NOT NULL REFERENCES "object" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
