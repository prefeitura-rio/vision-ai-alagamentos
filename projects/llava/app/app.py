# -*- coding: utf-8 -*-
import argparse
import asyncio
import base64
import os
import traceback
from io import BytesIO

import requests
import torch
import uvicorn
from fastapi import FastAPI, Request
from PIL import Image
from transformers import TextIteratorStreamer

from llava.constants import (
    DEFAULT_IM_END_TOKEN,
    DEFAULT_IM_START_TOKEN,
    DEFAULT_IMAGE_TOKEN,
    IMAGE_TOKEN_INDEX,
)
from llava.mm_utils import process_images, tokenizer_image_token
from llava.model.builder import load_pretrained_model
from llava.utils import build_logger

logger = build_logger("model", "model.log")
global_counter = 0
model_semaphore = asyncio.Semaphore(1)


def load_image(image_raw):

    image = None

    if image_raw.startswith("http://") or image_raw.startswith("https://"):
        timeout = int(os.getenv("REQUEST_TIMEOUT", "3"))
        response = requests.get(image_raw, timeout=timeout)
        image = Image.open(BytesIO(response.content))
    elif image_raw.lower().endswith(("png", "jpg", "jpeg", "webp", "gif")):
        image = Image.open(image_raw)
    elif image_raw.startswith("data:"):
        image_raw = image_raw.split(",")[1]
        image = Image.open(BytesIO(base64.b64decode(image_raw)))
    else:
        image = Image.open(BytesIO(base64.b64decode(image_raw)))

    return image


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

    def generate_output(self, params):
        tokenizer, model, image_processor = self.tokenizer, self.model, self.image_processor

        prompt = params["prompt"]
        ori_prompt = prompt
        images = params.get("images", None)

        if images is None or type(images) is not list:
            raise ValueError("Must be sent a list of images")

        if len(images) != prompt.count(DEFAULT_IMAGE_TOKEN):
            raise ValueError("Number of images does not match number of <image> tokens in prompt")

        images = [load_image(image) for image in images]
        image_sizes = [image.size for image in images]
        images = process_images(images, image_processor, model.config)

        images = [image.to(self.model.device, dtype=torch.float16) for image in images]

        replace_token = DEFAULT_IMAGE_TOKEN
        if getattr(self.model.config, "mm_use_im_start_end", False):
            replace_token = DEFAULT_IM_START_TOKEN + replace_token + DEFAULT_IM_END_TOKEN
        prompt = prompt.replace(DEFAULT_IMAGE_TOKEN, replace_token)

        num_image_tokens = prompt.count(replace_token) * model.get_vision_tower().num_patches
        image_args = {"images": images, "image_sizes": image_sizes}

        temperature = float(params.get("temperature", 1.0))
        top_p = float(params.get("top_p", 1.0))
        max_context_length = getattr(model.config, "max_position_embeddings", 2048)
        max_new_tokens = min(int(params.get("max_new_tokens", 256)), 1024)
        do_sample = True if temperature > 0.001 else False

        input_ids = (
            tokenizer_image_token(prompt, tokenizer, IMAGE_TOKEN_INDEX, return_tensors="pt")
            .unsqueeze(0)
            .to(self.device)
        )
        streamer = TextIteratorStreamer(
            tokenizer, skip_prompt=True, skip_special_tokens=True, timeout=15
        )

        max_new_tokens = min(
            max_new_tokens, max_context_length - input_ids.shape[-1] - num_image_tokens
        )

        if max_new_tokens < 1:
            return ori_prompt + "Exceeds max token length. Please start a new conversation, thanks."

        output_ids = model.generate(
            inputs=input_ids,
            do_sample=do_sample,
            temperature=temperature,
            top_p=top_p,
            max_new_tokens=max_new_tokens,
            streamer=streamer,
            use_cache=True,
            **image_args,
        )

        return tokenizer.batch_decode(output_ids, skip_special_tokens=True)[0].strip()


app = FastAPI()


@app.post("/")
async def run_model(request: Request):
    global model_semaphore, global_counter

    global_counter += 1
    params = await request.json()

    await model_semaphore.acquire()

    try:
        text = worker.generate_output(params)
        error_code = 0
    except ValueError as e:
        print("Caught ValueError:", e)
        text = e
        error_code = 1
    except torch.cuda.CudaError as e:
        print("Caught torch.cuda.CudaError:", e)
        text = "Internal Server Error"
        error_code = 2
    except Exception as e:
        print("Caught Unknown Error", e)
        print(traceback.format_exc())
        text = "Internal Server Error"
        error_code = 3
    finally:
        model_semaphore.release()

    return {"text": text, "error_code": error_code}


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

    model_semaphore = asyncio.Semaphore(args.limit_model_concurrency)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
