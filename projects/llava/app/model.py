import base64
import logging
import os
import threading
import traceback
import time
import uuid
from argparse import ArgumentParser
from dataclasses import dataclass
from io import BytesIO
from typing import Any

import requests
import torch
import zmq
from diskcache import Cache
from PIL import Image
from transformers import (
    BitsAndBytesConfig,
    LlavaNextForConditionalGeneration,
    LlavaNextProcessor,
)


def load_image(image_raw: str) -> Image.Image:
    if image_raw.startswith("http://") or image_raw.startswith("https://"):
        timeout = int(os.getenv("REQUEST_TIMEOUT", "3"))
        return Image.open(requests.get(image_raw, timeout=timeout, stream=True).raw)

    if image_raw.lower().endswith(("png", "jpg", "jpeg", "webp", "gif")):
        return Image.open(image_raw)

    if image_raw.startswith("data:"):
        image_raw = image_raw.split(",")[1]

    return Image.open(BytesIO(base64.b64decode(image_raw)))


def parser_prompt(params) -> tuple[str, list[Image.Image]]:
    prompt = params.get("prompt", None)
    images = params.get("images", None)

    if prompt is None:
        raise ValueError("Must be sent a prompt")

    if images is None or type(images) is not list:
        raise ValueError("Must be sent a list of images")

    if len(images) != prompt.count("<image>"):
        raise ValueError("Number of images does not match number of <image> tokens in prompt")

    return prompt, [load_image(image) for image in images]


@dataclass
class ModelParams:
    temperature: float
    top_p: float
    top_k: int
    max_length: int
    do_sample: bool

    def __init__(self, params: dict[str, Any]):
        self.temperature = float(params.get("temperature", 0.2))
        self.top_p = float(params.get("top_p", 1.0))
        self.top_k = int(params.get("top_k", 32))
        self.max_length = min(int(params.get("max_length", 256)), 1024)
        self.do_sample = True if self.temperature > 0.001 else False


class Model:
    def __init__(self):
        model_name = "llava-hf/llava-v1.6-34b-hf"
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )

        model: LlavaNextForConditionalGeneration = (
            LlavaNextForConditionalGeneration.from_pretrained(
                model_name,
                quantization_config=quantization_config,
                device_map="auto",
                low_cpu_mem_usage=True,
                attn_implementation="flash_attention_2",
            )
        )
        self.model = model
        logging.debug("Model loaded")

        processor: LlavaNextProcessor = LlavaNextProcessor.from_pretrained(
            model_name,
            use_fast=False,
        )
        self.processor = processor
        logging.debug("Processor loaded")

    def generate_output(self, prompt: str | list[str], images: list[Image.Image], params: ModelParams):
        model, processor = self.model, self.processor

        inputs = processor(text=prompt, images=images, return_tensors="pt").to("cuda")

        output_ids = model.generate(
            **inputs,
            do_sample=params.do_sample,
            temperature=params.temperature,
            top_k=params.top_k,
            top_p=params.top_p,
            max_length=params.max_length,
            use_cache=True,
        )

        return [result.strip() for result in processor.batch_decode(output_ids, skip_special_tokens=True)]


def send_time(url_timer: str, sleep: int, context: zmq.Context | None = None):
    context = context or zmq.Context.instance()

    socket = context.socket(zmq.PAIR)
    socket.connect(url_timer)

    while True:
        time.sleep(sleep)
        socket.send_string("ping")
        socket.recv_string()


def queue(queue_url: str, model: Model, params: ModelParams, cache: Cache, context: zmq.Context | None = None):
    context = context or zmq.Context.instance()
    queue = []
    last_time = time.time()

    socket = context.socket(zmq.REP)
    socket.connect(queue_url)

    url_timer = f"inproc://timer-{uuid.uuid4()}"
    timer = context.socket(zmq.PAIR)
    timer.bind(url_timer)

    thread_timer = threading.Thread(target=send_time, args=(url_timer, 1))
    thread_timer.daemon = True
    thread_timer.start()

    poller = zmq.Poller()
    poller.register(timer, zmq.POLLIN)
    poller.register(socket, zmq.POLLIN)

    while True:
        try:
            socks = dict(poller.poll())

            if socks.get(timer) == zmq.POLLIN:
                timer.recv_string()
                timer.send_string("pong")
                logging.debug("timer ping")

            if socks.get(socket) == zmq.POLLIN:
                message = socket.recv_pyobj()
                logging.debug(f"received queue request: {message}")
                id = uuid.uuid4()
                queue.append((id, message))
                socket.send_pyobj(id)

            now = time.time()

            if len(queue) >= 5 or (now - last_time >= 10 and len(queue) > 0):
                prompts = []
                images = []
                ids = []

                for id, message in queue:
                    prompts.append(message["prompt"])
                    images += message["images"]
                    ids.append(id)

                logging.debug("starting batch inferance")
                responses = model.generate_output(prompts, images, params)

                for id, response in zip(ids, responses):
                    logging.debug(f"complete inferance: {id}")
                    cache.set(id, response, expire=120)

                queue = []

            if now - last_time >= 10:
                logging.debug(f"queue size: {len(queue)}")
                last_time = now


        except Exception as e:
            logging.error("Caught Unknown Error", e)
            logging.error(traceback.format_exc())


def worker(worker_url: str, queue_url: str, cache: Cache, context: zmq.Context | None = None):
    context = context or zmq.Context.instance()
    max_retries = 200

    socket = context.socket(zmq.REP)
    socket.connect(worker_url)

    queue = context.socket(zmq.REQ)
    queue.connect(queue_url)

    while True:
        try:
            message = socket.recv_pyobj()
            logging.debug(f"Received worker request: {message}")

            try:
                prompt, images = parser_prompt(message)
                queue.send_pyobj({"prompt": prompt, "images": images})
                id = queue.recv_pyobj()
                text = cache.get(id)
                retries = 0

                while text is None and retries <= max_retries:
                    time.sleep(1)
                    retries += 1
                    text = cache.get(id)

                error_code = 0
                if text is None:
                    logging.error("Inferance Timeout")
                    text = "Inferance Timeout"
                    error_code = 3
            except ValueError as e:
                logging.error("Caught ValueError:", e)
                text = e
                error_code = 1
            except Exception as e:
                logging.error("Caught Unknown Error", e)
                logging.error(traceback.format_exc())
                text = "Internal Server Error"
                error_code = 2

            socket.send_pyobj({"text": text, "error_code": error_code})
        except Exception as e:
            logging.error("Caught Unknown Error", e)
            logging.error(traceback.format_exc())


if __name__ == "__main__":
    parser = ArgumentParser(description="Serve model")
    parser.add_argument("--listen-address", default="tcp://127.0.0.1:5555")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    logging.debug("Starting model")
    model = Model()

    url_worker = "inproc://workers"
    url_client = args.listen_address
    url_queue_router = "inproc://queues_router"
    url_queue_dealer = "inproc://queues_dealer"

    context = zmq.Context.instance()

    clients = context.socket(zmq.ROUTER)
    clients.bind(url_client)
    logging.debug("Binded clients")

    workers = context.socket(zmq.DEALER)
    workers.bind(url_worker)
    logging.debug("Binded workers")

    queues_router = context.socket(zmq.ROUTER)
    queues_router.bind(url_queue_router)
    logging.debug("Binded queues router")

    queues_dealer = context.socket(zmq.DEALER)
    queues_dealer.bind(url_queue_dealer)
    logging.debug("Binded queues dealer")

    cache = Cache()

    for _ in range(10):
        thread = threading.Thread(target=worker, args=(url_worker, url_queue_router, cache))
        thread.daemon = True
        thread.start()
    logging.info("Workers started")

    for _ in range(1):
        thread = threading.Thread(target=queue, args=(url_queue_dealer, model, ModelParams({}), cache))
        thread.daemon = True
        thread.start()
    logging.info("Queues started")


    logging.info("starting polling")
    poller = zmq.Poller()
    poller.register(clients, zmq.POLLIN)
    poller.register(workers, zmq.POLLIN)
    poller.register(queues_router, zmq.POLLIN)
    poller.register(queues_dealer, zmq.POLLIN)

    while True:
        socks = dict(poller.poll())

        if socks.get(clients) == zmq.POLLIN:
            logging.debug("sending message to worker")
            workers.send_multipart(clients.recv_multipart())

        if socks.get(workers) == zmq.POLLIN:
            logging.debug("sending message to client")
            clients.send_multipart(workers.recv_multipart())

        if socks.get(queues_router) == zmq.POLLIN:
            logging.debug("sending message to queue dealer")
            queues_dealer.send_multipart(queues_router.recv_multipart())

        if socks.get(queues_dealer) == zmq.POLLIN:
            logging.debug("sending message to queue router")
            queues_router.send_multipart(queues_dealer.recv_multipart())
