# -*- coding: utf-8 -*-
from app import config

TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "host": config.DATABASE_HOST,
                "port": config.DATABASE_PORT,
                "user": config.DATABASE_USER,
                "password": config.DATABASE_PASSWORD,
                "database": config.DATABASE_NAME,
            },
        }
    },
    "apps": {
        "app": {
            "models": [
                "aerich.models",
                "app.models",
            ],
            "default_connection": "default",
        },
    },
}
