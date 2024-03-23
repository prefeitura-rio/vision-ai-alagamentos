# -*- coding: utf-8 -*-
import zmq
from flask import Flask, request

server = Flask(__name__)
zmq_url = "tcp://127.0.0.1:5555"


@server.post("/")
def run_model():
    params = request.get_json()
    context = zmq.Context()
    with context.socket(zmq.REQ) as socket:
        socket.connect(zmq_url)
        socket.send_pyobj(params)
        response = socket.recv_pyobj()
        return response