# -*- coding: utf-8 -*-
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "cameraidentification" ADD "label_explanation" TEXT;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "cameraidentification" DROP COLUMN "label_explanation";"""
