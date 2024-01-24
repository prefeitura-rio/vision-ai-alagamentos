# -*- coding: utf-8 -*-
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "agent" ADD "auth_sub" VARCHAR(255) NOT NULL UNIQUE;
        CREATE UNIQUE INDEX "uid_agent_auth_su_ec014c" ON "agent" ("auth_sub");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX "idx_agent_auth_su_ec014c";
        ALTER TABLE "agent" DROP COLUMN "auth_sub";"""
