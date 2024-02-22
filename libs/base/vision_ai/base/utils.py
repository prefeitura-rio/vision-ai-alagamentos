# -*- coding: utf-8 -*-
from datetime import datetime

import pytz


def get_datetime() -> str:
    timestamp = datetime.now(pytz.timezone("America/Sao_Paulo"))
    return timestamp.strftime("%Y-%m-%dT%H:%M:%S.%f")
