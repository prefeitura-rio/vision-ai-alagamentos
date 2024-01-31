#!/bin/bash

sudo apt-get update -y || exit 1
sudo apt-get install -y ca-certificates curl || exit 1
sudo install -m 0755 -d /etc/apt/keyrings || exit 1
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc || exit 1
sudo chmod a+r /etc/apt/keyrings/docker.asc || exit 1

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null || exit 1
sudo apt-get update -y || exit 1

sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin || exit 1

sudo systemctl enable docker.service || exit 1
sudo systemctl enable containerd.service || exit 1
