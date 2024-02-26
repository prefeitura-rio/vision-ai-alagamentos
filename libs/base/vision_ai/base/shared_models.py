# -*- coding: utf-8 -*-
import json
import textwrap
from typing import List, Union

from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field


class Object(BaseModel):
    object: str = Field(description="The object from the objects table")
    label_explanation: str = Field(
        description="Highly detailed visual description of the image given the object context"
    )
    label: Union[bool, str, None] = Field(
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


def get_parser():
    # Create the output parser using the Pydantic model
    output_parser = PydanticOutputParser(pydantic_object=Output)

    # Valid JSON string
    output_example_str = str(OutputFactory().generate_sample().dict()).replace("'", '"')

    output_example_str = textwrap.dedent(output_example_str)
    output_example = output_parser.parse(output_example_str)
    output_example_parsed = json.dumps(output_example.dict(), indent=4)

    output_schema = json.loads(output_parser.pydantic_object.schema_json())
    output_schema_parsed = json.dumps(output_schema, indent=4)

    return output_parser, output_schema_parsed, output_example_parsed
