#!/usr/bin/env bash
gcloud --project=datario storage ls 'gs://datario-public/vision-ai/prod/ano=2024/mes=03/dia=23/**/*.png' > snapshots.txt
