# -*- coding: utf-8 -*-
from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "cameraidentification" ADD "label_id" UUID;
        ALTER TABLE "cameraidentification" DROP COLUMN "label";
        ALTER TABLE "cameraidentification" ALTER COLUMN "object_id" DROP NOT NULL;
        CREATE TABLE IF NOT EXISTS "label" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "value" VARCHAR(255) NOT NULL,
    "criteria" TEXT NOT NULL,
    "identification_guide" TEXT NOT NULL,
    "object_id" UUID NOT NULL REFERENCES "object" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_label_object__5c5639" UNIQUE ("object_id", "value")
);
        ALTER TABLE "cameraidentification" ADD CONSTRAINT "fk_cameraid_label_238d10dd" FOREIGN KEY ("label_id") REFERENCES "label" ("id") ON DELETE CASCADE;"""  # noqa


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "cameraidentification" DROP CONSTRAINT "fk_cameraid_label_238d10dd";
        ALTER TABLE "cameraidentification" ADD "label" BOOL;
        ALTER TABLE "cameraidentification" DROP COLUMN "label_id";
        ALTER TABLE "cameraidentification" ALTER COLUMN "object_id" SET NOT NULL;
        DROP TABLE IF EXISTS "label";
        CREATE UNIQUE INDEX "uid_cameraident_camera__7064a0" ON "cameraidentification" ("camera_id", "object_id");"""  # noqa
