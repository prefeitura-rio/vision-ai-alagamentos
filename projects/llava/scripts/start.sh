#!/bin/bash
python app/model.py &
gunicorn &
wait
