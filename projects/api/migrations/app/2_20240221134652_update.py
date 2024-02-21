# -*- coding: utf-8 -*-
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "user_identification" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "timestamp" TIMESTAMPTZ NOT NULL,
    "username" VARCHAR(255) NOT NULL,
    "identification_id" UUID NOT NULL REFERENCES "identification" ("id") ON DELETE CASCADE,
    "label_id" UUID NOT NULL REFERENCES "label" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_teste_usernam_f77621" UNIQUE ("username", "identification_id")
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "user_identification";"""
