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
from transformers import (
    BitsAndBytesConfig,
    LlavaNextForConditionalGeneration,
    LlavaNextProcessor,
)


def load_image(image_raw: str):
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
        model_name = "llava-hf/llava-v1.6-34b-hf"
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )

        model: LlavaNextForConditionalGeneration = LlavaNextForConditionalGeneration.from_pretrained(
            model_name,
            quantization_config=quantization_config,
            device_map="auto",
            low_cpu_mem_usage=True,
            attn_implementation="flash_attention_2",
        )
        self.model = model
        logging.info("Model loaded")

        processor: LlavaNextProcessor = LlavaNextProcessor.from_pretrained(model_name, use_fast=False)
        self.processor = processor
        logging.info("Processor loaded")

    # TODO: remover dependencia do git do LLaVA
    # TODO: separar validação de parametros da execução do modelo
    # TODO: fazer inferencia por batch
    def generate_output(self, params):
        model, processor = self.model, self.processor

        prompt = params["prompt"]
        images = params.get("images", None)

        if images is None or type(images) is not list:
            raise ValueError("Must be sent a list of images")

        if len(images) != prompt.count("<image>"):
            raise ValueError("Number of images does not match number of <image> tokens in prompt")

        images = [load_image(image) for image in images]
        temperature = float(params.get("temperature", 0.2))
        top_p = float(params.get("top_p", 1.0))
        top_k = int(params.get("top_k", 32))
        max_length = min(int(params.get("max_length", 256)), 1024)
        do_sample = True if temperature > 0.001 else False

        inputs = processor(text=prompt, images=images, return_tensors="pt").to("cuda")

        output_ids = model.generate(
            **inputs,
            do_sample=do_sample,
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            max_length=max_length,
            use_cache=True,
        )

        return processor.batch_decode(output_ids, skip_special_tokens=True)[0].strip()


# TODO: criar uma pipline de processamento em batch
# 1. validar parametros
# 2. baixar imagem
# 3. puxar parametros para fila de requisições
# 4. retornar id da requisição
# 5. ficar verificando reposta da requisição em um cache de memória
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
