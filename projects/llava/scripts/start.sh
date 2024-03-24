#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd ..
python app/model.py &
gunicorn &
cd $SCRIPT_DIR
wait
