#!/bin/env python
# -*- coding: utf-8 -*-
import sys
import time

import requests

sizes = [10, 25, 50, 75, 100, 250, 500, 750, 1000, 2000, 3000]

if len(sys.argv) != 4:
    print(f"Usage: {sys.argv[0]} <api_base_url> <oidc_username> <oidc_password>")
    exit(1)

base_url = sys.argv[1]
tokenData = {
    "username": sys.argv[2],
    "password": sys.argv[3],
}

response = requests.post(f"{base_url}/auth/token", data=tokenData)
if response.status_code >= 300 or response.status_code < 200:
    print(f"error getsing token {response.status_code}: {response.text}")
    exit(1)

token = response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

cameras = []
for size in sizes:
    cameras = []
    page = 1
    initial = time.time()

    while len(cameras) < 3000:
        response = requests.get(
            f"{base_url}/cameras?page={page}&size={size}",
            headers=headers,
        )
        if response.status_code >= 300 or response.status_code < 200:
            print(f"error getting cameras {response.status_code}: {response.text}")
            exit(1)
        data = response.json()
        cameras += data["items"]
        page += 1
        if data["page"] >= data["pages"]:
            break
    print(f"{sys.argv[0]} size {size} with {len(cameras)} cameras: {time.time()-initial:.2f}s")
