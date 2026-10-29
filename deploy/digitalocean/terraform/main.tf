# ==============================================================================
# AdventureTogether - DigitalOcean Production Infrastructure (Terraform/OpenTofu)
# ==============================================================================
# Provisions complete, hardened DigitalOcean infrastructure:
# - DigitalOcean Project grouping
# - Dedicated Private VPC Network
# - SSH Key pair handling (uploaded, existing, or generated)
# - Secure random secret generation for Django and PostgreSQL
# - Droplet compute instance with automated Cloud-Init provisioning
# - Optional Reserved IPv4 (Floating IP) assignment (existing or freshly allocated)
# - Optional DigitalOcean Managed DNS Domain & Records (A & CNAME)
# - DigitalOcean Cloud Firewall enforcing strict inbound/outbound policies
# ==============================================================================

provider "digitalocean" {
  token = var.do_token
}

# ------------------------------------------------------------------------------
# 1. Random Secrets & Password Generation
# ------------------------------------------------------------------------------

resource "random_password" "django_secret_key" {
  length  = 50
  special = true
}

resource "random_password" "postgres_password" {
  length  = 32
  special = false # Alphanumeric string avoids URL-encoding issues in DB connection strings
}

# ------------------------------------------------------------------------------
# 2. SSH Key Management
# ------------------------------------------------------------------------------

# Option A: Look up existing registered SSH key by name if provided
data "digitalocean_ssh_key" "existing" {
  count = var.ssh_key_name != "" ? 1 : 0
  name  = var.ssh_key_name
}

# Option B: Create new SSH key on DigitalOcean if public key text is provided
resource "digitalocean_ssh_key" "provided" {
  count      = var.ssh_key_name == "" && var.ssh_public_key != "" ? 1 : 0
  name       = "adventuretogether-${var.environment}-deployer"
  public_key = var.ssh_public_key
}

# Option C: Generate a fresh ED25519 keypair if no key is provided
resource "tls_private_key" "auto_generated" {
  count     = var.ssh_key_name == "" && var.ssh_public_key == "" ? 1 : 0
  algorithm = "ED25519"
}

resource "digitalocean_ssh_key" "auto_generated" {
  count      = var.ssh_key_name == "" && var.ssh_public_key == "" ? 1 : 0
  name       = "adventuretogether-${var.environment}-auto-key"
  public_key = tls_private_key.auto_generated[0].public_key_openssh
}

resource "local_sensitive_file" "auto_generated_private_key" {
  count           = var.ssh_key_name == "" && var.ssh_public_key == "" ? 1 : 0
  content         = tls_private_key.auto_generated[0].private_key_pem
  filename        = "${path.module}/id_ed25519"
  file_permission = "0600"
}

locals {
  ssh_key_id = (
    var.ssh_key_name != "" ? data.digitalocean_ssh_key.existing[0].id :
    var.ssh_public_key != "" ? digitalocean_ssh_key.provided[0].id :
    digitalocean_ssh_key.auto_generated[0].id
  )

  ssh_public_key_string = (
    var.ssh_key_name != "" ? data.digitalocean_ssh_key.existing[0].public_key :
    var.ssh_public_key != "" ? var.ssh_public_key :
    tls_private_key.auto_generated[0].public_key_openssh
  )
}

# ------------------------------------------------------------------------------
# 3. Dedicated VPC Network
# ------------------------------------------------------------------------------

resource "digitalocean_vpc" "app_vpc" {
  name        = "adventuretogether-${var.environment}-vpc-${var.region}"
  region      = var.region
  description = "Isolated private network for AdventureTogether ${var.environment} services"
  ip_range    = "10.10.0.0/16"
}

# ------------------------------------------------------------------------------
# 4. Droplet Virtual Machine
# ------------------------------------------------------------------------------

locals {
  # Computed allowed hosts for Django security headers
  django_allowed_hosts = join(",", compact([
    "localhost",
    "127.0.0.1",
    var.domain_name != "" ? var.domain_name : "",
    var.domain_name != "" ? "www.${var.domain_name}" : "",
    var.existing_reserved_ipv4 != "" ? var.existing_reserved_ipv4 : "",
    "*" # Permissive fallback for initial IP resolution
  ]))
}

resource "digitalocean_droplet" "app_server" {
  name       = var.droplet_name
  region     = var.region
  size       = var.droplet_size
  image      = var.droplet_image
  vpc_uuid   = digitalocean_vpc.app_vpc.id
  ssh_keys   = [local.ssh_key_id]
  backups    = true
  ipv6       = true
  monitoring = true
  tags       = ["adventuretogether", var.environment, "monorepo", "postgis", "django"]

  user_data = templatefile("${path.module}/templates/cloud-init.yaml.tftpl", {
    ssh_public_key       = local.ssh_public_key_string
    git_repository_url   = var.git_repository_url
    git_branch           = var.git_branch
    django_debug         = var.django_debug ? "True" : "False"
    django_secret_key    = random_password.django_secret_key.result
    django_allowed_hosts = local.django_allowed_hosts
    django_q_workers     = var.django_q_workers
    postgres_db_name     = var.postgres_db_name
    postgres_user        = var.postgres_user
    postgres_password    = random_password.postgres_password.result
    domain_name          = var.domain_name != "" ? var.domain_name : "none"
    admin_email          = var.admin_email
  })
}

# ------------------------------------------------------------------------------
# 5. Reserved IPv4 (Floating IP) Binding
# ------------------------------------------------------------------------------

# Case 1: Allocate a new static Reserved IP if requested and no existing IP is given
resource "digitalocean_reserved_ip" "new_ip" {
  count      = var.allocate_reserved_ipv4 && var.existing_reserved_ipv4 == "" ? 1 : 0
  region     = var.region
  droplet_id = digitalocean_droplet.app_server.id
}

# Case 2: Bind an existing user-provided Reserved IP address to the Droplet
resource "digitalocean_reserved_ip_assignment" "existing_ip_binding" {
  count      = var.existing_reserved_ipv4 != "" ? 1 : 0
  ip_address = var.existing_reserved_ipv4
  droplet_id = digitalocean_droplet.app_server.id
}

locals {
  # Resolve the effective public IPv4 address used for DNS and user access
  effective_public_ipv4 = (
    var.existing_reserved_ipv4 != "" ? var.existing_reserved_ipv4 :
    var.allocate_reserved_ipv4 ? digitalocean_reserved_ip.new_ip[0].ip_address :
    digitalocean_droplet.app_server.ipv4_address
  )
}

# ------------------------------------------------------------------------------
# 6. DigitalOcean DNS Domain & Records (Optional)
# ------------------------------------------------------------------------------

resource "digitalocean_domain" "app_domain" {
  count      = var.domain_name != "" && var.create_dns_records ? 1 : 0
  name       = var.domain_name
  ip_address = local.effective_public_ipv4
}

resource "digitalocean_record" "www_cname" {
  count  = var.domain_name != "" && var.create_dns_records ? 1 : 0
  domain = digitalocean_domain.app_domain[0].id
  type   = "CNAME"
  name   = "www"
  value  = "@"
  ttl    = 1800
}

# ------------------------------------------------------------------------------
# 7. Cloud Firewall Hardening
# ------------------------------------------------------------------------------

resource "digitalocean_firewall" "app_firewall" {
  name        = "adventuretogether-${var.environment}-firewall"
  droplet_ids = [digitalocean_droplet.app_server.id]

  # Inbound Rules: SSH, HTTP, HTTPS, ICMP Ping
  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "icmp"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Outbound Rules: Full DNS, HTTP/HTTPS for OpenStreetMap/Wikimedia API harvester, NTP, ICMP
  outbound_rule {
    protocol              = "tcp"
    port_range            = "53"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "53"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "tcp"
    port_range            = "80"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "tcp"
    port_range            = "443"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "123"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

# ------------------------------------------------------------------------------
# 8. DigitalOcean Project Organization
# ------------------------------------------------------------------------------

resource "digitalocean_project" "app_project" {
  name        = var.project_name
  description = "AdventureTogether Monorepo - Geospatial Scavenger Hunt & Open Data Ingestion Platform"
  purpose     = "Web Application"
  environment = var.environment == "production" ? "Production" : "Development"

  resources = compact([
    digitalocean_droplet.app_server.urn,
    var.domain_name != "" && var.create_dns_records ? digitalocean_domain.app_domain[0].urn : ""
  ])
}
