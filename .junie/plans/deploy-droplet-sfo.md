---
sessionId: session-261025-142218-v1o8
---

# Requirements

### Overview & Goals
The goal is to transition the AdventureTogether deployment model away from variable, consumption-based cloud services (such as DigitalOcean App Platform and Managed Database DBaaS clusters) to a self-contained, predictable, and cost-effective Virtual Machine (Droplet) deployment running in DigitalOcean's **SFO (San Francisco)** region.

By co-locating the containerized PostgreSQL/PostGIS database, Django API backend, Django-Q2 background harvester worker, and Vue 3 / Nginx frontend onto a single dedicated Droplet VM within an isolated private VPC, we achieve:
1. **Predictable, Fixed Cost**: Elimination of per-component and per-query consumption billing in favor of a fixed, predictable monthly expense ($24/month for a 2 vCPU / 4GB RAM instance).
2. **Maximum Resource Utilization**: Shared local compute and memory resources without inter-service network hops or database connection limits imposed by managed PaaS tiers.
3. **Low Latency & High Throughput**: Sub-millisecond internal communication between Django, PostGIS, and Django-Q2 via Docker's internal bridge network.
4. **Complete Infrastructure Ownership**: Full control over PostgreSQL configuration, PostGIS spatial extensions, automated daily backup retention, and host-level security.

### Scope
- **In Scope**:
  - OpenTofu / Terraform infrastructure configuration targeting DigitalOcean's **`sfo3`** (San Francisco 3) datacenter region.
  - Sizing recommendations and configuration for Droplet compute instances (`s-2vcpu-4gb` standard, `s-4vcpu-8gb` high capacity).
  - Provisioning of supplementary resources: Dedicated Private VPC (`10.10.0.0/16`), Static Reserved IPv4 (Floating IP), Cloud Firewall, Project organization, and DNS Domain / CNAME records.
  - Cloud-Init automated host bootstrapping: Docker & Docker Compose v2, UFW firewall, Fail2ban SSH protection, systemd unit for continuous stack lifecycle, automated daily PostGIS backup cron with 14-day rotation, and Let's Encrypt TLS via Certbot.
  - Automated deployment (`deploy.sh`) and destruction (`destroy.sh`) CLI runner scripts.
  - Unit and integration tests in `backend/apps/core/test_deployment_templates.py` and documentation in `documentation/digitalocean_deployment.md`.
  - Feature ledger tracking in `FEATURES.md`.
- **Out of Scope**:
  - Modifying backend Django business logic or Vue frontend application components.
  - App Platform or Managed Database cluster provisioning (deprecated in favor of Droplet VM hosting).
  - Multi-region active-active database replication.

### User Stories
- **As an Infrastructure Operator**, I want to deploy the entire AdventureTogether stack to DigitalOcean in the SFO region using a single CLI command with predictable monthly costs, so that I avoid unanticipated consumption billing spikes.
- **As a Scavenger Hunt Participant**, I want low-latency API responses and real-time quest synchronizations hosted close to the target geographic zone (SFO / West Coast), so that my location updates and submissions process smoothly.
- **As an Event Host**, I want my event data and spatial quest geometries protected by automated daily database backups and strict firewall policies, so that data loss and unauthorized access are prevented.

### Functional Requirements
1. **SFO Datacenter Targeting**: All cloud resources (VPC, Droplet, Reserved IP, Cloud Firewall) must default to DigitalOcean's `sfo3` datacenter.
2. **Droplet Sizing & Resource Allocation**:
   - Primary default plan: `s-2vcpu-4gb` (2 vCPUs, 4GB RAM, 80GB SSD, 4TB data transfer at $24/month).
   - High-concurrency alternative: `s-4vcpu-8gb` (4 vCPUs, 8GB RAM, 160GB SSD, 5TB data transfer at $48/month).
   - Development alternative: `s-2vcpu-2gb` (2 vCPUs, 2GB RAM, 60GB SSD, 3TB data transfer at $18/month).
3. **Zero-Consumption Service Stack**: Execute all 4 core services via `docker compose` on the Droplet:
   - `db`: `postgis/postgis:16-3.4` (PostgreSQL 16 + PostGIS 3.4 on internal port 5432).
   - `backend`: Django API + GeoDjango + DRF on port 8000.
   - `worker`: Django-Q2 ORM task cluster running `python manage.py qcluster`.
   - `frontend`: Vue 3 SPA built artifacts served by Nginx on port 80/443 with `/api/` reverse proxying.
4. **Static Reserved IPv4 & DNS Automation**: Support attaching an existing Reserved IP or automatically allocating a new static Reserved IP to decouple DNS routing from Droplet lifecycle events.
5. **Security & Backup Hardening**:
   - Inbound traffic restricted to ports `22` (SSH), `80` (HTTP), and `443` (HTTPS).
   - Daily PostGIS database dumps compressed to `/var/backups/adventuretogether/` with automatic 14-day pruning.
   - DigitalOcean weekly Droplet snapshot backups enabled (`backups = true`).
   - Automated HTTPS certificate provisioning using Certbot.

### Non-Functional Requirements
- **Cost Efficiency**: Minimize infrastructure expenditure while maximizing compute throughput and memory availability for PostGIS spatial indexing and Django-Q2 harvesting.
- **Reliability & Self-Healing**: Systemd service unit (`adventuretogether.service`) ensures automatic container stack restart upon Droplet reboot or crash.
- **Security**: Double-layer firewall protection (DigitalOcean Cloud Firewall at the edge + UFW on the host) and Fail2ban SSH defense.
- **Reproducibility**: 100% declarative Infrastructure-as-Code via OpenTofu / Terraform with automated pre-flight syntax and schema validation.

# Technical Design

### Current Implementation
The repository contains deployment assets in `deploy/digitalocean/`:
- `deploy/digitalocean/terraform/`: OpenTofu / Terraform templates (`main.tf`, `variables.tf`, `outputs.tf`, `versions.tf`, `templates/cloud-init.yaml.tftpl`) currently configured with `nyc3` defaults.
- `deploy/digitalocean/app-platform/app.yaml`: DigitalOcean App Platform specification for serverless/managed component deployment.
- `deploy/digitalocean/scripts/deploy.sh` & `destroy.sh`: Bash deployment helper scripts.
- `deploy/docker-compose.yml`: Multi-container specification defining `db` (PostGIS 16-3.4), `backend` (Django 5.x), `worker` (Django-Q2), and `frontend` (Vue 3 / Nginx).
- `backend/apps/core/test_deployment_templates.py`: Automated pytest suite testing IaC validity, Cloud-Init rendering, and script execution.

### Key Decisions
1. **Single Droplet Architecture over Multi-VM / Managed DBaaS**:
   - *Decision*: Host all containerized services (`db`, `backend`, `worker`, `frontend`) on a single dedicated Droplet VM.
   - *Rationale*: A single VM eliminates inter-service network latency, avoids connection pooling limits of managed DBaaS, simplifies volume management, and provides maximum utility and compute throughput per dollar ($24/month fixed vs $100+/month for segregated managed clusters).
2. **Region Selection: DigitalOcean `sfo3`**:
   - *Decision*: Standardize on DigitalOcean's modern `sfo3` (San Francisco 3) datacenter.
   - *Rationale*: `sfo3` provides modern Intel/AMD hypervisors, NVMe SSD storage, low latency to West Coast endpoints, and native support for VPC peering and Reserved IPs.
3. **Droplet Sizing Matrix**:
   - *Primary Recommendation (`s-2vcpu-4gb`, $24/month)*: 2 vCPUs, 4GB RAM, 80GB SSD. Provides sufficient RAM allocation: ~1GB for PostgreSQL/PostGIS shared buffers and spatial work memory, ~600MB for Django API workers, ~500MB for Django-Q2 harvester cluster, ~100MB for Nginx, and ~1.8GB for OS filesystem caching and buffer headroom.
   - *High-Scale Concurrency (`s-4vcpu-8gb`, $48/month)*: 4 vCPUs, 8GB RAM, 160GB SSD. Recommended for city-wide scavenger hunts with hundreds of concurrent teams submitting GPS tracks and photos simultaneously.
   - *Development / Staging (`s-2vcpu-2gb`, $18/month)*: 2 vCPUs, 2GB RAM, 60GB SSD. Suitable for staging environments with low submission frequency.
4. **Supplementary Infrastructure Resources Included**:
   - `digitalocean_vpc`: Isolated `10.10.0.0/16` network in `sfo3`.
   - `digitalocean_reserved_ip` & `digitalocean_reserved_ip_assignment`: Static public IPv4 ensuring zero IP changes during server maintenance or resizing.
   - `digitalocean_firewall`: Network-level edge firewall blocking unauthorized access to database and internal ports.
   - `digitalocean_project`: Logical resource grouping in the DigitalOcean control panel.
   - `digitalocean_domain` & `digitalocean_record`: Automated DNS record management.
   - Droplet Weekly Snapshot Backups (`backups = true`) alongside local daily PostGIS cron dumps.
5. **Host Orchestration & Swap Configuration**:
   - Configure a 2GB host swapfile in Cloud-Init to protect against out-of-memory (OOM) kernel terminations during burst spatial indexing.
   - Manage the Docker Compose lifecycle via a native systemd unit (`adventuretogether.service`).

### Architecture Diagram
```mermaid
graph TD
    Client[Users & Mobile Clients] -->|HTTPS / Port 443| EdgeFW[DigitalOcean Cloud Firewall\nInbound: 22, 80, 443]
    EdgeFW -->|Static IPv4| ResIP[DigitalOcean Reserved IP\nsfo3 Region]
    ResIP --> Droplet[DigitalOcean Droplet: s-2vcpu-4gb\nsfo3 Private VPC: 10.10.0.0/16]
    
    subgraph Droplet Stack [Droplet Host System (Ubuntu 24.04 LTS)]
        UFW[Host UFW Firewall & Fail2ban] --> Nginx[Frontend Container: Nginx\nPort 80/443 + Certbot TLS]
        Nginx -->|Static Assets| VueSPA[Vue 3 SPA Client]
        Nginx -->|/api/* & /admin/*| DjangoAPI[Backend Container: Django API\nGeoDjango + DRF / Port 8000]
        
        DjangoAPI -->|Spatial SQL| PostGIS[(db Container: PostGIS 16-3.4\nVolume: postgis_data / Port 5432)]
        Worker[worker Container: Django-Q2\nqcluster Harvester] -->|ORM Broker & Ingestion| PostGIS
        
        Cron[Host Cron Daemon] -->|Daily 02:00 UTC| BackupScript[backup_postgis.sh]
        BackupScript -->|Dump & 14-day Prune| BackupStore[/var/backups/adventuretogether/]
    end
    
    Worker -->|HTTPS Outbound| OSM[OpenStreetMap API]
    Worker -->|HTTPS Outbound| Wiki[Wikimedia & Wikidata APIs]
```

### Proposed Changes
1. **`deploy/digitalocean/terraform/variables.tf`**:
   - Change `region` default to `"sfo3"`.
   - Update `droplet_size` default to `"s-2vcpu-4gb"` with detailed docstring describing sizing options.
2. **`deploy/digitalocean/terraform/terraform.tfvars.example`**:
   - Update example configuration to reflect `sfo3`, `s-2vcpu-4gb`, and Reserved IP allocation.
3. **`deploy/digitalocean/terraform/templates/cloud-init.yaml.tftpl`**:
   - Add swapfile allocation (2GB) on boot.
   - Refine `adventuretogether.service` systemd unit and `/usr/local/bin/backup_postgis.sh` script.
4. **`deploy/digitalocean/scripts/deploy.sh` & `destroy.sh`**:
   - Update default region argument to `sfo3` and default size to `s-2vcpu-4gb`.
   - Ensure clean validation messages and parameter handling for SFO deployments.
5. **`documentation/digitalocean_deployment.md`**:
   - Update documentation to present Droplet deployment in `sfo3` as the primary standard architecture, detailing sizing, costs, VPC isolation, and operational maintenance.
6. **`backend/apps/core/test_deployment_templates.py`**:
   - Update pytest test assertions to validate `sfo3` defaults, sizing options, and Cloud-Init swapfile/backup configurations.
7. **`FEATURES.md`**:
   - Update `FEAT-011` feature description to record the SFO Droplet infrastructure conversion.

### Data Models / Contracts

#### Terraform Variable Schema (`variables.tf`)
```hcl
variable "do_token" {
  type        = string
  description = "DigitalOcean Personal Access Token with read and write permissions."
  sensitive   = true
}

variable "region" {
  type        = string
  description = "DigitalOcean datacenter region slug (default: sfo3 for San Francisco)."
  default     = "sfo3"
}

variable "droplet_size" {
  type        = string
  description = "DigitalOcean Droplet plan slug (recommended: s-2vcpu-4gb)."
  default     = "s-2vcpu-4gb"
}

variable "allocate_reserved_ipv4" {
  type        = bool
  description = "Whether to allocate a new static Reserved IPv4 address in sfo3."
  default     = false
}

variable "existing_reserved_ipv4" {
  type        = string
  description = "Optional existing Reserved IPv4 address to attach to the Droplet."
  default     = ""
}
```

#### Service Matrix on Droplet Host (`deploy/docker-compose.yml`)
| Service | Image / Build | Internal Port | Host Port | Purpose | Memory Budget |
|---|---|---|---|---|---|
| `db` | `postgis/postgis:16-3.4` | 5432 | 5432 (local) | PostGIS spatial persistence | ~1.0 GB |
| `backend` | `backend/Dockerfile` (Django 5.x) | 8000 | 8000 (local) | REST API & Admin | ~600 MB |
| `worker` | `backend/Dockerfile` (Django-Q2) | N/A | N/A | Background API harvester | ~500 MB |
| `frontend` | `frontend/Dockerfile` (Vue 3 / Nginx) | 80 | 80, 443 | Web UI & API Reverse Proxy | ~100 MB |

### File Structure
- Modified: `deploy/digitalocean/terraform/variables.tf`
- Modified: `deploy/digitalocean/terraform/terraform.tfvars.example`
- Modified: `deploy/digitalocean/terraform/templates/cloud-init.yaml.tftpl`
- Modified: `deploy/digitalocean/scripts/deploy.sh`
- Modified: `deploy/digitalocean/scripts/destroy.sh`
- Modified: `documentation/digitalocean_deployment.md`
- Modified: `backend/apps/core/test_deployment_templates.py`
- Modified: `FEATURES.md`

### Risks & Mitigations
- **Single Host Outage Risk**: Mitigated by allocating a static Reserved IP (enabling instant re-attachment to a newly provisioned replacement Droplet in `sfo3`) and maintaining both automated daily PostGIS SQL dumps and weekly DigitalOcean Droplet image snapshots.
- **Memory Pressure under Peak GeoJSON Queries**: Mitigated by configuring a 2GB SSD swapfile and sizing the base instance at `s-2vcpu-4gb` (4GB RAM) with an upgrade path to `s-4vcpu-8gb`.
- **Let's Encrypt DNS Propagation Delays**: Mitigated by non-blocking Cloud-Init SSL provisioning that logs warnings without halting container stack initialization.

# Testing

### Validation Approach
Verification of the Droplet deployment architecture will be conducted through automated unit and integration tests using `pytest` and IaC validation tools (`tofu validate` / `terraform validate`):
1. **Terraform / OpenTofu Syntax & Provider Validation**: Verify all HCL templates compile cleanly against the DigitalOcean provider schema with `sfo3` region settings.
2. **Cloud-Init Template Rendering & YAML Parsing**: Validate that `cloud-init.yaml.tftpl` renders with sample parameters into syntactically valid YAML containing all swapfile, Docker compose, backup script, and security definitions.
3. **Deployment Runner Script Tests**: Execute `./deploy/digitalocean/scripts/deploy.sh --help` and verify flag parsing, region defaults (`sfo3`), droplet sizing defaults (`s-2vcpu-4gb`), and token enforcement.
4. **Documentation & Feature Inventory Audit**: Confirm alignment across `documentation/digitalocean_deployment.md` and `FEATURES.md`.

### Key Scenarios
- **Scenario 1: Default SFO Droplet Configuration**:
  - Run `tofu validate` in `deploy/digitalocean/terraform/`.
  - Expect zero syntax errors, valid provider schema, and default region `sfo3`.
- **Scenario 2: Cloud-Init Bootstrap Generation**:
  - Render `cloud-init.yaml.tftpl` with mock variables.
  - Parse output with `yaml.safe_load()`.
  - Assert existence of `/etc/systemd/system/adventuretogether.service`, `/usr/local/bin/backup_postgis.sh`, `/etc/fail2ban/jail.local`, and swapfile creation directives.
- **Scenario 3: CLI Runner Parameter Execution**:
  - Invoke `deploy.sh --help` and verify `--region sfo3` and `--size s-2vcpu-4gb` documentation.
  - Invoke `deploy.sh` without tokens to ensure strict validation failure with clear diagnostic messaging.

### Test Changes
- **`backend/apps/core/test_deployment_templates.py`**:
  - Add test asserting default region in `variables.tf` and `deploy.sh` is `sfo3`.
  - Add test asserting `cloud-init.yaml.tftpl` contains swapfile allocation commands.
  - Add test asserting `variables.tf` droplet sizing options include `s-2vcpu-4gb`, `s-4vcpu-8gb`, and `s-2vcpu-2gb`.

# Delivery Steps

### ✓ Step 1: Update Terraform configuration and variables for SFO region and droplet sizing
The Terraform/OpenTofu templates are fully configured with SFO region defaults, optimized droplet sizing parameters, and all necessary auxiliary cloud resources.

- Update default region in `deploy/digitalocean/terraform/variables.tf` from `nyc3` to `sfo3` (San Francisco 3 datacenter).
- Set default `droplet_size` in `variables.tf` to `s-2vcpu-4gb` ($24/mo, 2 vCPUs / 4GB RAM / 80GB SSD / 4TB bandwidth) with inline documentation for high-capacity alternatives (`s-4vcpu-8gb`).
- Update `deploy/digitalocean/terraform/terraform.tfvars.example` to demonstrate `sfo3` datacenter configuration, static Reserved IPv4 assignment, custom domain routing, and Droplet snapshot backups.
- Verify `digitalocean_vpc` resource block binds to `sfo3` with IP range `10.10.0.0/16`.
- Ensure `digitalocean_droplet` instance configuration enables automated weekly cloud backups (`backups = true`), monitoring metrics (`monitoring = true`), and IPv6.
- Maintain existing `digitalocean_reserved_ip`, `digitalocean_firewall`, `digitalocean_domain`, and `digitalocean_project` definitions to ensure zero variable consumption overhead.

### ✓ Step 2: Enhance Cloud-Init bootstrap template and host orchestration
The Cloud-Init bootstrap template configures the host operating system, Docker Compose runtime, automated database backups, Let's Encrypt TLS certificates, and security defenses upon initial boot.

- Enhance `deploy/digitalocean/terraform/templates/cloud-init.yaml.tftpl` to configure a 2GB swapfile on the Droplet SSD to ensure resilience against memory spikes during high-volume geospatial indexing.
- Ensure the `adventuretogether.service` systemd unit manages the containerized stack (`postgis/postgis:16-3.4`, Django API, Django-Q2 harvester worker, Vue 3 SPA / Nginx) using `deploy/docker-compose.yml`.
- Validate the automated daily PostGIS backup script (`/usr/local/bin/backup_postgis.sh`) with gzip compression, permission hardening (`0700`), and 14-day retention pruning.
- Configure host-level UFW firewall and Fail2ban service to restrict inbound traffic to ports 22, 80, and 443 while isolating internal database and API ports.
- Refine Certbot automated SSL issuance and renewal logic for custom domain bindings.

### ✓ Step 3: Update deployment runner and teardown automation scripts for SFO Droplet workflow
The CLI deployment and teardown automation scripts support single-command provisioning and destruction targeting the SFO region.

- Update `deploy/digitalocean/scripts/deploy.sh` to default `--region` to `sfo3` and default `--size` to `s-2vcpu-4gb`.
- Update help and usage text in `deploy.sh` and `deploy/digitalocean/scripts/destroy.sh` to highlight SFO region deployment and Reserved IP options.
- Add pre-flight validation checks in `deploy.sh` verifying OpenTofu/Terraform binary availability, valid API token syntax, and connectivity.
- Verify `destroy.sh` safely deprovisions Droplets, firewalls, and VPC networks while preserving existing user-specified Reserved IPs when configured.

### ✓ Step 4: Update test suite, documentation guides, and feature inventory
The test suite, deployment documentation, and feature inventory comprehensively reflect the Droplet-based SFO architecture.

- Update `backend/apps/core/test_deployment_templates.py` to validate `sfo3` region defaults, Droplet sizing variables, Cloud-Init swapfile and backup directives, and script CLI parameters.
- Run `pytest backend/apps/core/test_deployment_templates.py` and `tofu validate` to ensure all IaC templates and test suites pass with 100% compliance.
- Expand `documentation/digitalocean_deployment.md` with detailed architectural explanations, Droplet sizing trade-off analysis, SFO region benefits, cost breakdown ($24/mo fixed vs variable App Platform pricing), and backup/restore runbooks.
- Update `FEATURES.md` feature ledger entry `FEAT-011` to document SFO Droplet-based infrastructure as the primary deployment pattern.