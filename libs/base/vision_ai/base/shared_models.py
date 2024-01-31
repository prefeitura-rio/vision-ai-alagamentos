# -*- coding: utf-8 -*-
from typing import List, Union

from pydantic import BaseModel, Field


class Object(BaseModel):
    object: str = Field(description="The object from the objects table")
    label_explanation: str = Field(
        description="Highly detailed visual description of the image given the object context"
    )
    label: Union[bool, str] = Field(
        description="Label indicating the condition or characteristic of the object"
    )


class ObjectFactory:
    @classmethod
    def generate_sample(cls) -> Object:
        return Object(
            object="<Object from objects table>",
            label_explanation="<Visual description of the image given the object context>",
            label="<Selected label from objects table>",
        )


class Output(BaseModel):
    objects: List[Object]


class OutputFactory:
    @classmethod
    def generate_sample(cls) -> Output:
        return Output(objects=[ObjectFactory.generate_sample()])
