# -*- coding: utf-8 -*-
from tortoise import fields
from tortoise.models import Model


class Agent(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255, unique=True)
    slug = fields.CharField(max_length=255, unique=True)
    auth_sub = fields.CharField(max_length=255, unique=True, index=True)
    last_heartbeat = fields.DatetimeField(null=True)
    cameras = fields.ManyToManyField("app.Camera")


class Camera(Model):
    id = fields.CharField(max_length=30, pk=True)
    name = fields.CharField(max_length=255, null=True)
    rtsp_url = fields.CharField(max_length=255, unique=True)
    update_interval = fields.IntField()
    latitude = fields.FloatField()
    longitude = fields.FloatField()
    objects = fields.ManyToManyField("app.Object")
    snapshots: fields.ReverseRelation["Snapshot"]
    agents: fields.ManyToManyRelation[Agent]


class Snapshot(Model):
    id = fields.UUIDField(pk=True)
    url = fields.CharField(max_length=255)
    timestamp = fields.DatetimeField()
    camera = fields.ForeignKeyField("app.Camera")
    identifications = fields.ReverseRelation["Identification"]


class Identification(Model):
    id = fields.UUIDField(pk=True)
    snapshot = fields.ForeignKeyField("app.Snapshot")
    label = fields.ForeignKeyField("app.Label")
    timestamp = fields.DatetimeField()
    label_explanation = fields.TextField()


class Label(Model):
    id = fields.UUIDField(pk=True)
    object = fields.ForeignKeyField("app.Object", related_name="labels")
    value = fields.CharField(max_length=255)
    criteria = fields.TextField()
    identification_guide = fields.TextField()

    class Meta:
        unique_together = (("object", "value"),)


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


class Object(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255, unique=True)
    slug = fields.CharField(max_length=255, unique=True)
    title = fields.CharField(max_length=255, unique=True)
    explanation = fields.TextField()
    cameras: fields.ManyToManyRelation[Camera]
    prompts: fields.ManyToManyRelation[Prompt]
