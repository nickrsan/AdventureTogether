# ==============================================================================
# AdventureTogether - DigitalOcean Infrastructure Variables
# ==============================================================================
# This file declares all input variables for provisioning the AdventureTogether
# infrastructure on DigitalOcean, including authentication, droplet sizing,
# networking, reserved IP binding, and DNS domain routing.
# ==============================================================================

variable "do_token" {
  type        = string
  description = "DigitalOcean Personal Access Token (API token) with read and write permissions."
  sensitive   = true

  validation {
    condition     = length(var.do_token) > 0
    error_message = "A valid DigitalOcean API token (do_token) is required for provisioning."
  }
}

variable "region" {
  type        = string
  description = "DigitalOcean datacenter region slug (e.g. sfo3, nyc3, ams3, fra1, sgp1). Default is sfo3 for San Francisco."
  default     = "sfo3"
}

variable "environment" {
  type        = string
  description = "Deployment environment stage (production, staging, or development)."
  default     = "production"
}

variable "project_name" {
  type        = string
  description = "Display name of the DigitalOcean Project used to group all associated resources."
  default     = "AdventureTogether"
}

variable "droplet_name" {
  type        = string
  description = "Hostname for the primary AdventureTogether application Droplet."
  default     = "adventuretogether-app"
}

variable "droplet_size" {
  type        = string
  description = "DigitalOcean Droplet plan slug. Recommended standard is s-2vcpu-4gb ($24/mo, 2 vCPUs, 4GB RAM) for PostgreSQL+PostGIS, Django, Django-Q2, and Nginx. High capacity alternative: s-4vcpu-8gb ($48/mo). Development alternative: s-2vcpu-2gb ($18/mo)."
  default     = "s-2vcpu-4gb"
}

variable "droplet_image" {
  type        = string
  description = "Operating system image slug for the Droplet. Ubuntu 24.04 LTS is standard."
  default     = "ubuntu-24-04-x64"
}

variable "ssh_public_key" {
  type        = string
  description = "SSH public key content (e.g. 'ssh-ed25519 AAA...' or 'ssh-rsa AAA...') for root/deployer access. If empty and ssh_key_name is not set, a local keypair will be generated."
  default     = ""
}

variable "ssh_key_name" {
  type        = string
  description = "Optional name of an existing SSH key already registered in your DigitalOcean account."
  default     = ""
}

variable "existing_reserved_ipv4" {
  type        = string
  description = "Optional pre-existing DigitalOcean Reserved IPv4 address to attach to this Droplet (leave empty to not bind an existing reserved IP)."
  default     = ""
}

variable "allocate_reserved_ipv4" {
  type        = bool
  description = "Whether to allocate a new DigitalOcean Reserved IPv4 address and attach it to the Droplet if no existing_reserved_ipv4 is supplied."
  default     = false
}

variable "domain_name" {
  type        = string
  description = "Optional domain or subdomain name for the application (e.g. 'adventure.example.com' or 'example.com'). If provided, DNS and SSL certificates will be configured."
  default     = ""
}

variable "create_dns_records" {
  type        = bool
  description = "Whether to manage DNS Domain and A/CNAME records in DigitalOcean DNS when domain_name is specified."
  default     = true
}

variable "admin_email" {
  type        = string
  description = "Administrator email address for Let's Encrypt TLS certificate generation and urgent notifications."
  default     = "admin@example.com"
}

variable "git_repository_url" {
  type        = string
  description = "Git repository clone URL used to deploy the AdventureTogether codebase onto the Droplet."
  default     = "https://github.com/AdventureTogether/AdventureTogether.git"
}

variable "git_branch" {
  type        = string
  description = "Git branch to check out during automated provisioning."
  default     = "main"
}

variable "postgres_db_name" {
  type        = string
  description = "PostgreSQL spatial database name."
  default     = "adventure_together"
}

variable "postgres_user" {
  type        = string
  description = "PostgreSQL superuser username."
  default     = "postgres"
}

variable "django_debug" {
  type        = bool
  description = "Enable or disable Django DEBUG mode. Must be false in production environments."
  default     = false
}

variable "django_q_workers" {
  type        = number
  description = "Number of parallel worker processes for the Django-Q2 ORM task cluster."
  default     = 4
}
