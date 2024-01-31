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

resource "google_compute_instance" "stream-server" {
  name         = "stream-server-vision-ai-benchmarking"
  tags         = ["bench-vision-ai"]
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
  }
  metadata_startup_script = <<SCRIPT
  ${file("${path.module}/scripts/install-docker-ubuntu.sh")}
  SCRIPT
}

resource "google_compute_instance" "send-stream" {
  count        = 10
  name         = "send-server-vision-ai-benchmarking-${count.index}"
  tags         = ["bench-vision-ai"]
  machine_type = var.send_stream_machine_type
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
  ${file("${path.module}/scripts/install-docker-ubuntu.sh")}
  SCRIPT
}

resource "google_compute_instance" "api" {
  name         = "api-vision-ai-benchmarking"
  tags         = ["bench-vision-ai"]
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
  }
  metadata_startup_script = <<SCRIPT
  ${file("${path.module}/scripts/install-docker-ubuntu.sh")}
  SCRIPT
}

resource "google_compute_instance" "agent" {
  name         = "agent-vision-ai-benchmarking"
  tags         = ["bench-vision-ai"]
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
  ${file("${path.module}/scripts/install-docker-ubuntu.sh")}
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
