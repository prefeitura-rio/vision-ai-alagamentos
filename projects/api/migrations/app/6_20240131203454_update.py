# -*- coding: utf-8 -*-
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "camera" ADD "snapshot_timestamp" TIMESTAMPTZ;
        ALTER TABLE "camera" ADD "snapshot_url" VARCHAR(255);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "camera" DROP COLUMN "snapshot_timestamp";
        ALTER TABLE "camera" DROP COLUMN "snapshot_url";"""
