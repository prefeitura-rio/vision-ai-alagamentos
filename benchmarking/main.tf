terraform {
  backend "gcs" {
    prefix = "terraform-bench-vision-ai"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

data "terraform_remote_state" "project_id" {
  backend   = "gcs"
  workspace = terraform.workspace

  config = {
    bucket = var.bucket
    prefix = "terraform-state"
  }
}

resource "random_uuid" "agent_id" {
}

locals {
  env                   = <<ENV
  export INFISICAL_ADDRESS=${var.infisical_address}
  export INFISICAL_TOKEN=${var.infisical_token}
  export INFISICAL_ENVIRONMENT=${var.infisical_environment}
  export AGENT_URL=http://${google_compute_address.api.address}:8080/agents/${random_uuid.agent_id.result}/cameras
  export CAMERA_URL=http://${google_compute_address.api.address}:8080/cameras
  export HEARTBEAT_URL=http://${google_compute_address.api.address}:8080/agents/${random_uuid.agent_id.result}/heartbeat
ENV
  install_docker_ubuntu = file("${path.module}/scripts/install-docker-ubuntu.sh")
  start_docker_compose  = file("${path.module}/scripts/start-docker-compose.sh")
  docker_compose = {
    stream_server = file("${path.module}/docker/stream-server.docker-compose.yaml")
    send_server   = templatefile("${path.module}/docker/send-server.docker-compose.yaml.tftpl", { server_ip = google_compute_address.stream_server_ip.address })
    api           = file("${path.module}/docker/api.docker-compose.yaml")
    agent         = file("${path.module}/docker/agent.docker-compose.yaml")
  }
  dockerfile = {
    send_server = file("${path.module}/docker/send-server.Dockerfile")
  }
  stream_video = file("${path.module}/scripts/stream-video.sh")
}

resource "google_compute_firewall" "rules" {
  name    = "vision-ai-benchmarking"
  network = var.network
  allow {
    protocol = "all"
  }
  source_tags = ["vision-ai-benchmarking"]
  target_tags = ["vision-ai-benchmarking"]
}

resource "google_compute_address" "stream_server_ip" {
  name         = "stream-server-ip"
  region       = var.region
  subnetwork   = var.subnetwork
  address_type = "INTERNAL"
  purpose      = "GCE_ENDPOINT"
}

resource "google_compute_instance" "stream_server" {
  name         = "stream-server-vision-ai-benchmarking"
  tags         = ["vision-ai-benchmarking"]
  machine_type = var.stream_server_machine_type
  zone         = var.zone
  boot_disk {
    initialize_params {
      size  = 10
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
    }
  }
  scheduling {
    provisioning_model          = "SPOT"
    preemptible                 = true
    automatic_restart           = false
    instance_termination_action = "STOP"
  }
  network_interface {
    network    = var.network
    subnetwork = var.subnetwork
    network_ip = google_compute_address.stream_server_ip.address
  }
  metadata_startup_script = <<SCRIPT
  mkdir -p /scripts

  echo '${local.install_docker_ubuntu}' > /scripts/install-docker.sh || exit 1
  echo '${local.start_docker_compose}' > /scripts/start-docker-compose.sh || exit 1
  echo '${local.docker_compose.stream_server}' > /home/ubuntu/docker-compose.yaml || exit 1

  chmod +x /scripts/install-docker.sh /scripts/start-docker-compose.sh || exit 1

  /scripts/install-docker.sh || exit 1
  /scripts/start-docker-compose.sh || exit 1
  SCRIPT
}

resource "google_compute_instance" "send_server" {
  count        = 10
  name         = "send-server-vision-ai-benchmarking-${count.index}"
  tags         = ["vision-ai-benchmarking"]
  machine_type = var.send_server_machine_type
  zone         = var.zone
  boot_disk {
    initialize_params {
      size  = 10
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
    }
  }
  scheduling {
    provisioning_model          = "SPOT"
    preemptible                 = true
    automatic_restart           = false
    instance_termination_action = "STOP"
  }
  network_interface {
    network    = var.network
    subnetwork = var.subnetwork
  }
  metadata_startup_script = <<SCRIPT
  mkdir -p /scripts

  echo '${local.install_docker_ubuntu}' > /scripts/install-docker.sh || exit 1
  echo '${local.start_docker_compose}' > /scripts/start-docker-compose.sh || exit 1
  echo '${local.docker_compose.send_server}' > /home/ubuntu/docker-compose.yaml || exit 1
  echo '${local.dockerfile.send_server}' > /home/ubuntu/Dockerfile || exit 1
  echo '${local.stream_video}' > /home/ubuntu/stream-video.sh.template || exit 1
  MACHINE_ID=${count.index} envsubst '$${MACHINE_ID}' < /home/ubuntu/stream-video.sh.template > /home/ubuntu/stream-video.sh

  chmod +x /scripts/install-docker.sh /scripts/start-docker-compose.sh || exit 1

  /scripts/install-docker.sh || exit 1
  /scripts/start-docker-compose.sh || exit 1
  SCRIPT
}

resource "google_compute_address" "api" {
  name         = "api-ip"
  region       = var.region
  subnetwork   = var.subnetwork
  address_type = "INTERNAL"
  purpose      = "GCE_ENDPOINT"
}

resource "google_compute_instance" "api" {
  name         = "api-vision-ai-benchmarking"
  tags         = ["vision-ai-benchmarking"]
  machine_type = var.api_machine_type
  zone         = var.zone
  boot_disk {
    initialize_params {
      size  = 10
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
    }
  }
  scheduling {
    provisioning_model          = "SPOT"
    preemptible                 = true
    automatic_restart           = false
    instance_termination_action = "STOP"
  }
  network_interface {
    network    = var.network
    subnetwork = var.subnetwork
    network_ip = google_compute_address.api.address
  }
  metadata_startup_script = <<SCRIPT
  mkdir -p /scripts

  echo '${local.install_docker_ubuntu}' > /scripts/install-docker.sh || exit 1
  echo '${local.start_docker_compose}' > /scripts/start-docker-compose.sh || exit 1
  echo '${local.docker_compose.api}' > /home/ubuntu/docker-compose.yaml || exit 1
  echo '${local.env}' > /home/ubuntu/.env || exit 1

  chmod +x /scripts/install-docker.sh /scripts/start-docker-compose.sh || exit 1

  /scripts/install-docker.sh || exit 1
  /scripts/start-docker-compose.sh || exit 1
  SCRIPT
}

resource "google_compute_instance" "agent" {
  name         = "agent-vision-ai-benchmarking"
  tags         = ["vision-ai-benchmarking"]
  machine_type = var.agent_machine_type
  zone         = var.zone
  boot_disk {
    initialize_params {
      size  = 10
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
    }
  }
  scheduling {
    provisioning_model          = "SPOT"
    preemptible                 = true
    automatic_restart           = false
    instance_termination_action = "STOP"
  }
  network_interface {
    network    = var.network
    subnetwork = var.subnetwork
  }
  metadata_startup_script = <<SCRIPT
  mkdir -p /scripts

  echo '${local.install_docker_ubuntu}' > /scripts/install-docker.sh || exit 1
  echo '${local.start_docker_compose}' > /scripts/start-docker-compose.sh || exit 1
  echo '${local.docker_compose.agent}' > /home/ubuntu/docker-compose.yaml || exit 1
  echo '${local.env}' > /home/ubuntu/env.yaml || exit 1

  chmod +x /scripts/install-docker.sh /scripts/start-docker-compose.sh || exit 1

  /scripts/install-docker.sh || exit 1
  #/scripts/start-docker-compose.sh || exit 1
  SCRIPT
}

module "cloud_router" {
  source  = "terraform-google-modules/cloud-router/google"
  version = "~> 6.0"
  name    = "vision-ai-benchmarking-cloud-router"
  project = var.project_id
  network = var.network
  region  = var.region

  nats = [{
    name                               = "vision-ai-benchmarking-nat-gateway"
    source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"
    subnetworks = [
      {
        name                    = var.subnetwork
        source_ip_ranges_to_nat = ["PRIMARY_IP_RANGE"]
      }
    ]
  }]
}
