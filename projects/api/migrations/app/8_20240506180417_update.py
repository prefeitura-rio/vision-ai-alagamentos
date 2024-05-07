# -*- coding: utf-8 -*-
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "identification_marker" ADD "all_users" BOOL NOT NULL  DEFAULT True;
        CREATE TABLE IF NOT EXISTS "whitelist_identification" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "username" VARCHAR(255) NOT NULL,
    "identification_id" UUID NOT NULL REFERENCES "identification" ("id") ON DELETE CASCADE
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "identification_marker" DROP COLUMN "all_users";
        DROP TABLE IF EXISTS "whitelist_identification";"""
