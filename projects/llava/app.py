# -*- coding: utf-8 -*-
import argparse

import uvicorn
from fastapi import FastAPI

from llava.model.builder import load_pretrained_model
from llava.utils import build_logger

logger = build_logger("model", "model.log")


class Model:
    def __init__(
        self,
        model_path,
        model_base,
        model_name,
        load_8bit,
        load_4bit,
        device,
        use_flash_attn,
    ):
        if model_path.endswith("/"):
            model_path = model_path[:-1]
        if model_name is None:
            model_paths = model_path.split("/")
            if model_paths[-1].startswith("checkpoint-"):
                self.model_name = model_paths[-2] + "_" + model_paths[-1]
            else:
                self.model_name = model_paths[-1]
        else:
            self.model_name = model_name

        self.device = device
        logger.info(f"Loading the model {self.model_name}")
        self.tokenizer, self.model, self.image_processor, self.context_len = load_pretrained_model(
            model_path,
            model_base,
            self.model_name,
            load_8bit,
            load_4bit,
            device=self.device,
            use_flash_attn=use_flash_attn,
        )
        self.is_multimodal = "llava" in self.model_name.lower()


app = FastAPI()


@app.post("/")
async def run_model():
    output = "Hello"
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="localhost")
    parser.add_argument("--port", type=int, default=40000)
    parser.add_argument("--model-path", type=str, default="liuhaotian/llava-v1.5-7b")
    parser.add_argument("--model-base", type=str, default=None)
    parser.add_argument("--model-name", type=str)
    parser.add_argument("--load-8bit", action="store_true")
    parser.add_argument("--load-4bit", action="store_true")
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--use-flash-attn", action="store_true")
    parser.add_argument("--limit-model-concurrency", type=int, default=5)
    args = parser.parse_args()
    logger.info(f"args: {args}")

    worker = Model(
        args.model_path,
        args.model_base,
        args.model_name,
        args.load_8bit,
        args.load_4bit,
        args.device,
        args.use_flash_attn,
    )

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
