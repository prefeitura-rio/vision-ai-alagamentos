#!/bin/env python
# -*- coding: utf-8 -*-
import csv
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

response = requests.get(f"{base_url}/agents", headers=headers)
if response.status_code >= 300 or response.status_code < 200:
    print(f"error getting agents {response.status_code}: {response.text}")
    exit(1)

data = response.json()
agents = [item for item in data["items"] if item["name"] == "vision-ai-agent-1"]
if len(agents) == 0:
    print("vision-ai-agent-1 not found")
    exit(1)

with open(path_csv) as csvfile:
    spamreader = csv.DictReader(csvfile, delimiter=",", quotechar='"')
    for row in spamreader:
        response = requests.post(
            f"{base_url}/cameras",
            headers=headers,
            json=row,
        )
        if response.status_code == 422:
            print(f"já existe {row['id']}")
        elif response.status_code >= 300 or response.status_code < 200:
            print(f"error creating camera {response.status_code}: {response.text}")
            exit(1)
        else:
            print(f"foi adicionado {row['id']} com sucesso")
        response = requests.post(
            f"{base_url}/agents/{agents[0]['id']}/cameras/{row['id']}",
            headers=headers,
        )
        if response.status_code >= 300 or response.status_code < 200:
            print(f"error adding camera to agent {response.status_code}: {response.text}")
            exit(1)
