# -*- coding: utf-8 -*-
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "label" ADD "order" INT NOT NULL DEFAULT 0;
        ALTER TABLE "label" ADD "text" TEXT NOT NULL DEFAULT 'Vazio';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "label" DROP COLUMN "order";
        ALTER TABLE "label" DROP COLUMN "text";"""
