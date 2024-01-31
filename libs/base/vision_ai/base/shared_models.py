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


class Output(BaseModel):
    objects: List[Object]
