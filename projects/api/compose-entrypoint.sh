#!/bin/sh
if [ ! -d "./migrations/app/" ]; then
    echo "Migrations folder does not exist, ASSUMING FIRST RUN"

    echo "Running aerich init-db to create initial migration"
    aerich init-db || true

else
    echo "./migrations/app/ folder exist, skipping initialization"
fi

echo "Running Migrations"
aerich upgrade

uvicorn app.main:app --host 0.0.0.0 --port 8080
