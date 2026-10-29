# DigitalOcean SFO Droplet Deployment & Infrastructure Automation Guide

This guide details how to deploy the complete AdventureTogether platform onto a self-contained, predictable Virtual Machine (Droplet) in DigitalOcean's **SFO (San Francisco)** datacenter region using OpenTofu / Terraform and Cloud-Init.

---

## 1. Overview & Architecture Rationale

AdventureTogether standardizes on a **single dedicated Virtual Machine (Droplet)** deployment model within DigitalOcean's **`sfo3` (San Francisco 3)** datacenter region rather than variable, consumption-based cloud services (such as DigitalOcean App Platform and Managed Database DBaaS clusters).

### Key Architectural Benefits:
1. **Predictable, Fixed Monthly Cost**:
   - Replaces variable per-query and component-based consumption billing with a fixed monthly rate ($24/month for standard 2 vCPU / 4GB RAM instance).
2. **Resource Efficiency & Zero Inter-Service Overhead**:
   - PostgreSQL/PostGIS, Django REST API, Django-Q2 background harvester worker, and Vue 3 / Nginx frontend communicate over local Docker bridge networking with sub-millisecond query latency.
3. **Optimized Geographic Placement (SFO Region)**:
   - Hosting in DigitalOcean's modern `sfo3` datacenter provides low latency for West Coast participants, high-speed NVMe SSD storage, and direct VPC peering support.
4. **Complete Data & Backup Ownership**:
   - Direct control over PostGIS spatial extensions, automated daily database dumps to local storage with 14-day retention, and weekly DigitalOcean Droplet image snapshots.

---

## 2. Infrastructure Topology

```
[ Internet Traffic / Mobile Clients ]
        │
        ▼ (Port 80 / 443, ICMP)
[ DigitalOcean Cloud Firewall (Edge Inbound: 22, 80, 443) ]
        │
        ▼
[ DigitalOcean Static Reserved IPv4 (sfo3) ] ─── (Automated DNS & Let's Encrypt TLS)
        │
        ▼
[ DigitalOcean Droplet: s-2vcpu-4gb (Ubuntu 24.04 LTS / sfo3 VPC: 10.10.0.0/16) ]
  │
  ├── [ 2GB SSD Host Swapfile ] (OOM spike prevention during spatial indexing)
  │
  ├── [ Nginx Web Reverse Proxy (Port 80 / 443) ]
  │         │
  │         ├──> [ / : Vue 3 SPA (Single Page Application) ]
  │         │
  │         └──> [ /api/* & /admin/* : Django REST + GeoDjango (Port 8000) ]
  │                     │
  │                     ├──> [ PostgreSQL 16 + PostGIS 3.4 (Port 5432) ]
  │                     │           ▲
  │                     │           │ (PostgreSQL ORM Broker)
  │                     └──> [ Django-Q2 Harvester Worker (qcluster) ]
  │
  ├── [ Automated Cron Backups: Daily PostGIS dumps to /var/backups/adventuretogether ]
  └── [ Host UFW Firewall & Fail2ban SSH Defense ]
```

---

## 3. Droplet Sizing & Resource Allocation Matrix

| Tier | Droplet Slug | Hardware Specs | Monthly Cost | Ideal Use Case | Memory Allocation Plan |
|---|---|---|---|---|---|
| **Standard (Recommended)** | `s-2vcpu-4gb` | 2 vCPUs, 4GB RAM, 80GB SSD, 4TB Transfer | **$24/mo** | Standard production hunts, up to 50 concurrent teams | PostGIS: ~1GB, Django: ~600MB, Worker: ~500MB, Nginx: ~100MB, OS/Buffer: ~1.8GB + 2GB Swap |
| **High Concurrency** | `s-4vcpu-8gb` | 4 vCPUs, 8GB RAM, 160GB SSD, 5TB Transfer | **$48/mo** | City-wide multi-thousand participant hunts | PostGIS: ~2.5GB, Django: ~1.5GB, Worker: ~1.5GB, Nginx: ~200MB, OS/Buffer: ~2.3GB + 2GB Swap |
| **Staging / Dev** | `s-2vcpu-2gb` | 2 vCPUs, 2GB RAM, 60GB SSD, 3TB Transfer | **$18/mo** | Development and QA test environments | PostGIS: ~600MB, Django: ~350MB, Worker: ~300MB, Nginx: ~50MB, OS/Buffer: ~700MB + 2GB Swap |

---

## 4. Quick Start: Zero-to-Deployed in One Command

Run the automated deployment script from the project root:

```bash
# Minimal deployment to sfo3 with API token only
./deploy/digitalocean/scripts/deploy.sh --token "dop_v1_your_token_here"
```

### Full Deployment with Domain, Static Reserved IP, and Custom Sizing:
```bash
./deploy/digitalocean/scripts/deploy.sh \
  --token "dop_v1_your_token_here" \
  --region "sfo3" \
  --size "s-2vcpu-4gb" \
  --domain "adventure.example.com" \
  --allocate-ip \
  --auto-approve
```

---

## 5. Declarative Terraform / OpenTofu Deployment

### Step 1: Navigate to Terraform Directory
```bash
cd deploy/digitalocean/terraform
```

### Step 2: Configure Variables
```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
# DigitalOcean API Token (Required)
do_token = "dop_v1_your_token_here"

# Datacenter Region (Default: sfo3 for San Francisco)
region = "sfo3"

# Sizing (Recommended: s-2vcpu-4gb)
droplet_size = "s-2vcpu-4gb"

# Optional Static Reserved IP Allocation:
allocate_reserved_ipv4 = true

# Optional Custom Domain & Automated DNS Setup:
domain_name        = "adventure.example.com"
create_dns_records = true
admin_email        = "admin@adventure.example.com"
```

### Step 3: Initialize and Apply
```bash
tofu init
tofu plan
tofu apply
```

### Step 4: Access Outputs & Automated Ansible Inventory
Once the run finishes, Terraform displays the connection endpoints and stages the auto-generated private key file:
```text
Outputs:
application_url           = "https://adventure.example.com"
api_health_check_url      = "https://adventure.example.com/api/health/"
effective_public_ipv4     = "143.198.123.45"
ssh_command               = "ssh -i deploy/digitalocean/terraform/id_ed25519 deploy@143.198.123.45"
ssh_private_key_path      = "deploy/digitalocean/terraform/id_ed25519"
ansible_deploy_command    = "ansible-playbook -i deploy/ansible/inventory.ini deploy/ansible/playbook.yml"
```

The auto-generated SSH private key is stored at `deploy/digitalocean/terraform/id_ed25519` with restricted `0600` permissions. The deployment runner automatically writes `deploy/ansible/inventory.ini` targeting the provisioned Droplet IP.

---

## 6. Automated Terraform-to-Ansible Bridge

When running `./deploy/digitalocean/scripts/deploy.sh`, the orchestrator automatically:
1. Provisions Droplet VM and VPC infrastructure via Terraform / OpenTofu.
2. Ensures the SSH private key is secured with mode `0600`.
3. Dynamically generates `deploy/ansible/inventory.ini` with host configuration:
   ```ini
   [app_servers]
   droplet ansible_host=143.198.123.45 ansible_user=deploy ansible_ssh_private_key_file=deploy/digitalocean/terraform/id_ed25519
   ```
4. Executes the Ansible application deployment playbook:
   ```bash
   ansible-playbook -i deploy/ansible/inventory.ini deploy/ansible/playbook.yml
   ```

To provision infrastructure without immediately executing Ansible, use the `--skip-ansible` flag:
```bash
./deploy/digitalocean/scripts/deploy.sh --token "<DO_API_TOKEN>" --skip-ansible
```

---

## 7. Dual Update Pathways & Zero-Data-Loss Migrations

When changes are committed to the `main` git branch, operators can update the live stack and apply Django database migrations without resetting PostgreSQL/PostGIS data or dropping active hunts.

### Pathway A: Local Update Runner (from Workstation or CI/CD)
Run the local update script from your development machine:
```bash
# Update Droplet stack over SSH (auto-detects IP and SSH key from inventory/Terraform)
./deploy/digitalocean/scripts/update.sh

# Or target a specific branch or Droplet IP:
./deploy/digitalocean/scripts/update.sh --ip "143.198.123.45" --branch "main"

# Or execute via Ansible playbook:
./deploy/digitalocean/scripts/update.sh --method ansible
```

### Pathway B: On-Droplet Maintenance Runner (Direct SSH or Webhook)
SSH onto the Droplet and execute the remote updater:
```bash
ssh -i deploy/digitalocean/terraform/id_ed25519 deploy@<DROPLET_IP>
/opt/adventuretogether/deploy/update.sh --branch main
```

### Zero-Data-Loss Update Sequence
Both update pathways enforce the following atomic execution sequence:
1. **Git Pull**: Fetches latest source code from repository `origin/main`.
2. **Docker Compose Build**: Rebuilds frontend, backend, and harvester images (`docker compose build --pull`).
3. **Database Health Verification**: Starts PostgreSQL/PostGIS and verifies `pg_isready`.
4. **Isolated Migration**: Runs `python manage.py migrate --noinput` inside an ephemeral container. If migrations fail, the update halts immediately without disrupting existing containers.
5. **Static File Collection**: Runs `python manage.py collectstatic --noinput`.
6. **Graceful Stack Switchover**: Executes `docker compose up -d --remove-orphans` to reload updated application containers.
7. **Health Verification**: Polls `http://localhost/api/health/` until HTTP 200 is confirmed.
8. **Volume Preservation**: Persistent volume `postgis_data` is strictly preserved across all updates and restarts.

---

## 8. Host Orchestration & Security Hardening

### Host Swap Space
Cloud-Init automatically configures a **2GB SSD swapfile** (`/swapfile`) on the Droplet host. This provides critical headroom to guard against kernel Out-Of-Memory (OOM) terminations during burst geospatial polygon indexing and bulk Changeset ingestion.

### Double-Layer Firewall Protection
- **Edge Layer (DigitalOcean Cloud Firewall)**: Drops all unsolicited packets at the datacenter boundary. Inbound access is strictly limited to ports `22` (SSH), `80` (HTTP), and `443` (HTTPS). Internal PostgreSQL (`5432`) and Django (`8000`) ports are inaccessible from the outside.
- **Host Layer (UFW & Fail2ban)**: Local host firewall enforces port restrictions. Fail2ban monitors SSH authentication and bans IP addresses attempting unauthorized logins.

### Systemd Service Lifecycle
The containerized stack is managed by the host systemd service unit `/etc/systemd/system/adventuretogether.service`. It automatically launches all 4 services via `docker compose` upon Droplet boot or reboot.

---

## 9. Automated Backups & Disaster Recovery Runbook

### Scheduled Daily PostGIS Dumps
- An automated cron job executes daily at `02:00 UTC` via `/usr/local/bin/backup_postgis.sh`.
- Dumps are compressed with gzip and stored in `/var/backups/adventuretogether/postgis_backup_<timestamp>.sql.gz` with restricted permissions (`0600`).
- Backups older than **14 days** are pruned automatically to conserve disk space.
- In addition, weekly DigitalOcean Droplet snapshot backups are enabled (`backups = true`).

### Manual Backup Creation
To generate an immediate database snapshot on demand:
```bash
ssh deploy@<DROPLET_IP> "sudo /usr/local/bin/backup_postgis.sh"
```

### Database Restore Procedure
To restore a PostGIS database dump:
```bash
ssh deploy@<DROPLET_IP>
gunzip < /var/backups/adventuretogether/postgis_backup_<timestamp>.sql.gz | docker exec -i adventure_together_db psql -U postgres -d adventure_together
```

---

## 10. Teardown & Deprovisioning

To completely deprovision all cloud resources:
```bash
./deploy/digitalocean/scripts/destroy.sh --token "dop_v1_your_token_here"
```
Or via OpenTofu:
```bash
cd deploy/digitalocean/terraform && tofu destroy
```
