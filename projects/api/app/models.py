# -*- coding: utf-8 -*-
from tortoise import fields
from tortoise.contrib.postgres.fields import ArrayField
from tortoise.models import Model
from tortoise.validators import MinValueValidator


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
    public_url = fields.CharField(max_length=255)
    timestamp = fields.DatetimeField(null=True)
    camera = fields.ForeignKeyField("app.Camera")
    identifications = fields.ReverseRelation["Identification"]


class Identification(Model):
    id = fields.UUIDField(pk=True)
    snapshot = fields.ForeignKeyField("app.Snapshot")
    label = fields.ForeignKeyField("app.Label")
    timestamp = fields.DatetimeField()
    label_explanation = fields.TextField()


class IdentificationMaker(Model):
    id = fields.UUIDField(pk=True)
    identification = fields.ForeignKeyField("app.Identification")
    tags = ArrayField(element_type="text", null=True)

    class Meta:
        table = "identification_marker"


class UserIdentification(Model):
    id = fields.UUIDField(pk=True)
    timestamp = fields.DatetimeField()
    username = fields.CharField(max_length=255)
    label = fields.ForeignKeyField("app.Label")
    identification = fields.ForeignKeyField("app.Identification")

    class Meta:
        table = "user_identification"
        unique_together = ("username", "identification")


class HideIdentification(Model):
    id = fields.UUIDField(pk=True)
    timestamp = fields.DatetimeField()
    identification = fields.ForeignKeyField("app.Identification")

    class Meta:
        table = "hide_identification"


class Label(Model):
    id = fields.UUIDField(pk=True)
    order = fields.IntField(default=0)
    object = fields.ForeignKeyField("app.Object", related_name="labels")
    value = fields.CharField(max_length=255)
    text = fields.TextField(default="Vazio")
    criteria = fields.TextField()
    identification_guide = fields.TextField()

    class Meta:
        unique_together = (("object", "value"),)
        # unique_together = (("object", "value"), ("object", "order"))
        ordering = ["object_id", "order"]


class PromptObject(Model):
    id = fields.UUIDField(pk=True)
    prompt = fields.ForeignKeyField("app.Prompt", related_name="objects")
    object = fields.ForeignKeyField("app.Object", related_name="prompts")
    order = fields.IntField(validators=[MinValueValidator(0)])

    class Meta:
        table = "prompt_object"
        unique_together = (("prompt", "object"), ("prompt", "order"))


class Prompt(Model):  # TODO: Add platform (GCP, OpenAI, etc.)
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255, unique=True)
    model = fields.CharField(max_length=255)
    prompt_text = fields.TextField()
    max_output_token = fields.IntField()
    temperature = fields.FloatField()
    top_k = fields.IntField()
    top_p = fields.FloatField()
    objects = fields.ReverseRelation["PromptObject"]


class Object(Model):
    id = fields.UUIDField(pk=True)
    name = fields.CharField(max_length=255, unique=True)
    slug = fields.CharField(max_length=255, unique=True)
    title = fields.CharField(max_length=255, unique=True, null=True)
    question = fields.TextField(null=True)
    explanation = fields.TextField(null=True)
    cameras: fields.ManyToManyRelation[Camera]
    prompts = fields.ReverseRelation["PromptObject"]
    labels = fields.ReverseRelation["Label"]
