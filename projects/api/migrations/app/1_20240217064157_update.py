# -*- coding: utf-8 -*-
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "prompt_object";
        CREATE TABLE IF NOT EXISTS "prompt_object" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "order" INT NOT NULL,
    "object_id" UUID NOT NULL REFERENCES "object" ("id") ON DELETE CASCADE,
    "prompt_id" UUID NOT NULL REFERENCES "prompt" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_prompt_obje_prompt__e6f871" UNIQUE ("prompt_id", "object_id"),
    CONSTRAINT "uid_prompt_obje_prompt__44ef5c" UNIQUE ("prompt_id", "order")
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "prompt_object";
        CREATE TABLE "prompt_object" (
    "object_id" UUID NOT NULL REFERENCES "object" ("id") ON DELETE CASCADE,
    "prompt_id" UUID NOT NULL REFERENCES "prompt" ("id") ON DELETE CASCADE
);"""
