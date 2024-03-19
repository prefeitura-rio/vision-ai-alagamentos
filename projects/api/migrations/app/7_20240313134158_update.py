# -*- coding: utf-8 -*-
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "hide_identification" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "timestamp" TIMESTAMPTZ NOT NULL,
    "identification_id" UUID NOT NULL REFERENCES "identification" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "hide_identification";"""
