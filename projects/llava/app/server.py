# -*- coding: utf-8 -*-
import zmq
from flask import Flask, request

server = Flask(__name__)

def start(model_address: str) -> Flask:
    server.config["MODEL_ADDRESS"] = model_address

    return server


@server.post("/")
def run_model():
    params = request.get_json()
    context = zmq.Context()
    with context.socket(zmq.REQ) as socket:
        socket.connect(server.config["MODEL_ADDRESS"])
        socket.send_pyobj(params)
        response = socket.recv_pyobj()
        return response
