# -*- coding: utf-8 -*-
from tortoise import fields
from tortoise.models import Model


class Agent(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255, unique=True)
    slug = fields.CharField(max_length=255, unique=True)
    auth_sub = fields.CharField(max_length=255, unique=True, index=True)
    last_heartbeat = fields.DatetimeField(null=True)
    cameras = fields.ManyToManyField("app.Camera", related_name="agents")


class Camera(Model):
    id = fields.CharField(max_length=30, pk=True)
    name = fields.CharField(max_length=255, null=True)
    rtsp_url = fields.CharField(max_length=255, unique=True)
    update_interval = fields.IntField()
    latitude = fields.FloatField()
    longitude = fields.FloatField()
    snapshot_url = fields.CharField(max_length=255, null=True)
    snapshot_timestamp = fields.DatetimeField(null=True)
    identifications = fields.ReverseRelation["Identification"]


class Identification(Model):
    id = fields.UUIDField(pk=True)
    camera = fields.ForeignKeyField("app.Camera", related_name="identifications")
    object = fields.ForeignKeyField("app.Object", related_name="identifications", null=True)
    label = fields.ForeignKeyField("app.Label", related_name="identifications", null=True)
    timestamp = fields.DatetimeField(null=True)
    label_explanation = fields.TextField(null=True)


class Label(Model):
    id = fields.UUIDField(pk=True)
    object = fields.ForeignKeyField("app.Object", related_name="labels")
    value = fields.CharField(max_length=255)
    criteria = fields.TextField()
    identification_guide = fields.TextField()

    class Meta:
        unique_together = (("object", "value"),)


class Object(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255, unique=True)
    slug = fields.CharField(max_length=255, unique=True)


class Prompt(Model):  # TODO: Add platform (GCP, OpenAI, etc.)
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255, unique=True)
    objects = fields.ManyToManyField("app.Object", related_name="prompts")
    model = fields.CharField(max_length=255)
    prompt_text = fields.TextField()
    max_output_token = fields.IntField()
    temperature = fields.FloatField()
    top_k = fields.IntField()
    top_p = fields.FloatField()
