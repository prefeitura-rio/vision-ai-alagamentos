variable "project_id" {
  description = "Google project ID"
  type        = string
}

variable "region" {
  description = "Google default region"
  type        = string
}

variable "zone" {
  description = "Google default zone"
  type        = string
}

variable "bucket" {
  description = "Google default bucket"
  type        = string
}

variable "network" {
  description = "Google default network"
  type        = string
}

variable "subnetwork" {
  description = "Google default subnetwork"
  type        = string
}

variable "stream_server_machine_type" {
  description = "Stream server machine type"
  type        = string
}

variable "send_stream_machine_type" {
  description = "Stream server machine type"
  type        = string
}

variable "api_machine_type" {
  description = "Stream server machine type"
  type        = string
}

variable "agent_machine_type" {
  description = "Stream server machine type"
  type        = string
}
