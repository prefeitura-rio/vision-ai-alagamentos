# -*- coding: utf-8 -*-
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "identification_marker" ADD "tags" text[];"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "identification_marker" DROP COLUMN "tags";"""
