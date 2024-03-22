import base64
import logging
import os
import pickle
import threading
import traceback
from argparse import ArgumentParser
from io import BytesIO

import requests
import torch
import zmq
from PIL import Image

from llava.constants import (
    DEFAULT_IM_END_TOKEN,
    DEFAULT_IM_START_TOKEN,
    DEFAULT_IMAGE_TOKEN,
    IMAGE_TOKEN_INDEX,
)
from llava.mm_utils import process_images, tokenizer_image_token
from llava.model.builder import load_pretrained_model


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
    def __init__(self):
        model_path = "liuhaotian/llava-v1.6-34b"
        model_name = "llava-v1.6-34b"

        self.tokenizer, self.model, self.image_processor, self.context_len = load_pretrained_model(
            model_path=model_path,
            model_base=None,
            model_name=model_name,
            load_8bit=False,
            load_4bit=True,
            device="cuda",
            use_flash_attn=True,
        )
        logging.info("Model loaded")

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

        images = [image.to(model.device, dtype=torch.float16) for image in images]

        replace_token = DEFAULT_IMAGE_TOKEN
        if getattr(model.config, "mm_use_im_start_end", False):
            replace_token = DEFAULT_IM_START_TOKEN + replace_token + DEFAULT_IM_END_TOKEN
        prompt = prompt.replace(DEFAULT_IMAGE_TOKEN, replace_token)

        image_args = {"images": images, "image_sizes": image_sizes}

        temperature = float(params.get("temperature", 0.2))
        top_p = float(params.get("top_p", 1.0))
        top_k = int(params.get("top_k", 32))
        max_length = min(int(params.get("max_length", 256)), 1024)
        do_sample = True if temperature > 0.001 else False

        input_ids = (
            tokenizer_image_token(prompt, tokenizer, IMAGE_TOKEN_INDEX, return_tensors="pt")
            .unsqueeze(0)
            .to("cuda")
        )

        if max_length < 1:
            return ori_prompt + "Exceeds max token length. Please start a new conversation, thanks."

        output_ids = model.generate(
            inputs=input_ids,
            do_sample=do_sample,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            max_length=max_length,
            use_cache=True,
            **image_args,
        )

        return tokenizer.batch_decode(output_ids, skip_special_tokens=True)[0].strip()


def worker(worker_url: str, model: Model, context=None):
    context = context or zmq.Context.instance()

    socket = context.socket(zmq.REP)
    socket.connect(worker_url)

    while True:
        message = pickle.loads(socket.recv())
        print(f"Received request: {message}")

        try:
            text = model.generate_output(message)
            error_code = 0
        except ValueError as e:
            logging.error("Caught ValueError:", e)
            text = e
            error_code = 1
        except Exception as e:
            logging.error("Caught Unknown Error", e)
            logging.error(traceback.format_exc())
            text = "Internal Server Error"
            error_code = 2

        socket.send(pickle.dumps({"text": text, "error_code": error_code}))


if __name__ == "__main__":
    parser = ArgumentParser(description="Serve model")
    parser.add_argument("--listen-address", default="tcp://127.0.0.1:5555")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    logging.info("Starting model")
    model = Model()
    url_worker = "inproc://workers"
    url_client = args.listen_address

    context = zmq.Context.instance()

    clients = context.socket(zmq.ROUTER)
    clients.bind(url_client)

    workers = context.socket(zmq.DEALER)
    workers.bind(url_worker)

    for i in range(5):
        thread = threading.Thread(target=worker, args=(url_worker, model))
        thread.daemon = True
        thread.start()

    zmq.proxy(clients, workers)

    clients.close()
    workers.close()
    context.term()
