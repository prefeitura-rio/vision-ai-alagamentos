# -*- coding: utf-8 -*-
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "identification_marker" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "identification_id" UUID NOT NULL REFERENCES "identification" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS "identification_marker";"""
