#!/bin/env python
# -*- coding: utf-8 -*-
import csv
import random
import sys

import requests

maxInt = sys.maxsize

while True:
    # decrease the maxInt value by factor 10
    # as long as the OverflowError occurs.

    try:
        csv.field_size_limit(maxInt)
        break
    except OverflowError:
        maxInt = int(maxInt / 10)

if len(sys.argv) != 5:
    print(f"Usage: {sys.argv[0]} <api_base_url> <username> <password> <path_csv>")
    exit(1)

base_url = sys.argv[1]
tokenData = {
    "username": sys.argv[2],
    "password": sys.argv[3],
}
path_csv = sys.argv[4]

response = requests.post(f"{base_url}/auth/token", data=tokenData)
if response.status_code >= 300 or response.status_code < 200:
    print(f"error getting token {response.status_code}: {response.text}")
    exit(1)

token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

response = requests.get(f"{base_url}/cameras?size=3000", headers=headers)
if response.status_code >= 300 or response.status_code < 200:
    print(f"error getting agents {response.status_code}: {response.text}")
    exit(1)

cameras = response.json()["items"]

with open(path_csv) as csvfile:
    spamreader = csv.DictReader(csvfile, delimiter=",", quotechar='"')
    for row in spamreader:
        response = requests.post(
            f"{base_url}/objects",
            headers=headers,
            json=row,
        )
        if response.status_code == 422:
            print(f"já existe {row['name']}")
        elif response.status_code >= 300 or response.status_code < 200:
            print(f"error creating camera {response.status_code}: {response.text}")
            exit(1)
        else:
            print(f"foi adicionado {row['name']} com sucesso")
        indexs_generate = [int(len(cameras) * random.random()) for _ in range(500)]
        object_id = response.json()["id"]
        for index in indexs_generate:
            response = requests.post(
                f"{base_url}/objects/{object_id}/cameras/{cameras[index]['id']}",
                headers=headers,
            )
            if response.status_code >= 300 or response.status_code < 200:
                print(f"error adding camera to agent {response.status_code}: {response.text}")
                exit(1)
