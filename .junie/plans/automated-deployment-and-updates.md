---
sessionId: session-261025-225722-1icn
---

# Requirements

### Overview & Goals
The objective of this initiative is to deliver a robust, highly reliable, and zero-downtime deployment and maintenance lifecycle for AdventureTogether on DigitalOcean. This ensures:
1. **Automated Zero-Touch Initial Deployment**: Upon completion of Terraform/OpenTofu provisioning, the infrastructure seamlessly transitions into full application orchestration (either via automated Cloud-Init / Ansible bridge or via explicit single-command Ansible execution), resolving the previous "blank Nginx site" issue.
2. **Deterministic SSH Key & Inventory Management**: Generated SSH private keys are persisted locally with hardened permissions (`0600`), and ready-to-use Ansible inventory files are generated automatically.
3. **State-Preserving Application Updates**: Operators can update the running stack to reflect changes on `main` via dual update pathways (local CLI runner / Ansible playbook or on-Droplet maintenance script) that apply Django database migrations and rebuild containers without resetting PostgreSQL/PostGIS data or interrupting service.

---

### Scope
#### In Scope
- **Root Cause Resolution**: Eliminate host-level Nginx port conflicts in Cloud-Init and ensure database migrations run during deployment.
- **Terraform-to-Ansible Bridge**: Update Terraform outputs and `deploy/digitalocean/scripts/deploy.sh` to extract the SSH private key, generate `deploy/ansible/inventory.ini`, and optionally invoke Ansible automatically.
- **Ansible Application Orchestration**: Update `deploy/ansible/roles/application/tasks/main.yml` and `playbook.yml` to template `.env`, sync source code, build Docker containers, and run `python manage.py migrate`.
- **Dual Update Pathways**:
  - Local script (`deploy/digitalocean/scripts/update.sh`) and Ansible playbook (`deploy/ansible/update.yml`) to update remote droplets from developer machines or CI.
  - Remote on-Droplet script (`/opt/adventuretogether/deploy/update.sh`) to update the stack directly on the VM.
- **Automated Validation**: Unit and integration tests in `backend/apps/core/test_deployment_templates.py` validating Terraform, Cloud-Init, Ansible syntax, and update scripts.
- **Documentation & Feature Ledger**: Comprehensive developer runbooks in `documentation/digitalocean_deployment.md`, updated `documentation/deployment_guide.md`, and registry entry in `FEATURES.md`.

#### Out of Scope
- Provisioning multi-node Kubernetes clusters (retaining standard fixed-cost single Droplet architecture).
- Modifying core application business logic in Django apps or Vue 3 frontend components.

---

### User Stories
- **As a Developer/Operator**, I want to run a single command (`./deploy.sh`) and have my DigitalOcean Droplet fully provisioned, configured, and running the live AdventureTogether application with all database tables created, so that I can immediately access the service without manual debugging.
- **As a DevOps Engineer**, I want clear paths to SSH keys and exact Ansible commands, so that I can inspect, manage, or re-run deployment playbooks against provisioned infrastructure deterministically.
- **As an Application Maintainer**, I want a one-command update mechanism that pulls the latest `main` branch, applies Django migrations, and restarts containers without deleting or resetting the PostGIS database volume, so that active hunts and submissions remain safe and persistent.

---

### Functional Requirements
1. **Host Nginx Elimination**: Cloud-Init must not install package `python3-certbot-nginx` or enable host Nginx daemons that intercept port `80`/`443`.
2. **Automated SSH Key Export**: When Terraform generates an ED25519 keypair, the private key must be saved to `deploy/digitalocean/terraform/id_ed25519` (with `chmod 600`) and referenced in Ansible inventory.
3. **Automated Inventory Generation**: Terraform / `deploy.sh` must output or write `deploy/ansible/inventory.ini` populated with the Droplet public IP, `deploy` user, and private key path.
4. **Initial Application & Migration Execution**: Ansible and Cloud-Init must ensure `docker compose up -d --build` is executed and database migrations (`python manage.py migrate --noinput`) succeed before declaring deployment complete.
5. **Dual Update Execution**:
   - Local: `./deploy/digitalocean/scripts/update.sh` (or `ansible-playbook -i deploy/ansible/inventory.ini deploy/ansible/update.yml`)
   - Remote: `ssh deploy@<IP> "/opt/adventuretogether/deploy/update.sh"`
6. **Data Safety**: Persistent volume `postgis_data` must remain preserved across builds, updates, and container restarts.
7. **Health Verification**: Update routines must verify HTTP `200 OK` on `/api/health/` before finalizing.

---

### Non-Functional Requirements
- **Reliability & Idempotency**: All Ansible playbooks and update scripts must be strictly idempotent (safe to run repeatedly without unintended side effects).
- **Security**: Private keys saved with mode `0600`; environment secrets (`POSTGRES_PASSWORD`, `DJANGO_SECRET_KEY`) stored with mode `0600` on the remote host; non-root execution via `deploy` user.
- **Performance**: Zero-downtime or sub-second container switchover during rolling Docker Compose updates.

# Technical Design

### Current Implementation & Root Cause Analysis
1. **The "Blank Nginx Site" Cause**:
   - In `deploy/digitalocean/terraform/templates/cloud-init.yaml.tftpl`, the system package list included `python3-certbot-nginx`. In Ubuntu 24.04 LTS, installing `python3-certbot-nginx` pulls in `nginx` as a system package dependency and starts the host Nginx daemon on port `80`.
   - The host Nginx daemon binds port 80 and serves the default Ubuntu placeholder page (`Welcome to nginx!`), conflicting with the Docker frontend container.
2. **Missing Django Migrations**:
   - In both Cloud-Init bootstrap and `deploy/docker-compose.yml`, the backend container starts `python manage.py runserver 0.0.0.0:8000` without running `python manage.py migrate`. Without migrations, database tables (`auth_user`, `events_event`, etc.) do not exist.
3. **SSH Key & Inventory Disconnect**:
   - Terraform generates an in-memory keypair when no key is supplied, but does not persist the private key to a dedicated file on disk.
   - `deploy/ansible/inventory.ini` hardcodes `localhost ansible_connection=local` instead of the provisioned Droplet IP.

---

### Key Decisions
1. **Automated Terraform-to-Ansible Bridge**:
   - *Decision*: `deploy/digitalocean/scripts/deploy.sh` will execute Terraform, write the SSH key to `deploy/digitalocean/terraform/id_ed25519` (permissions `0600`), generate `deploy/ansible/inventory.ini`, and automatically execute Ansible `deploy/ansible/playbook.yml`.
   - *Rationale*: Delivers a single-command zero-to-deployed experience while maintaining full decoupling and allowing operators to run Ansible directly anytime.
2. **Dual Local & Remote Update Scripts**:
   - *Decision*: Provide both a local orchestrator (`deploy/digitalocean/scripts/update.sh` / `deploy/ansible/update.yml`) and an on-Droplet updater (`/opt/adventuretogether/deploy/update.sh`).
   - *Rationale*: Supports developer workstations, automated CI/CD webhooks, and manual SSH maintenance workflows with identical migration and reload semantics.
3. **State Preservation Strategy**:
   - *Decision*: Retain named volume `postgis_data` in `deploy/docker-compose.yml` and execute `python manage.py migrate --noinput` during container startup/update before restarting dependent services.
   - *Rationale*: Protects application data and spatial indexes from being wiped during code updates.

---

### Proposed Changes

#### 1. Cloud-Init Template Hardening (`deploy/digitalocean/terraform/templates/cloud-init.yaml.tftpl`)
- Remove `python3-certbot-nginx` from package list; install standalone `certbot` only.
- Add pre-flight check disabling and stopping any host `nginx` service: `systemctl stop nginx || true; systemctl disable nginx || true`.
- Ensure Docker Compose runs `docker compose exec -T backend python manage.py migrate --noinput` and `docker compose exec -T backend python manage.py collectstatic --noinput`.

#### 2. Terraform Outputs & Local Key Export (`deploy/digitalocean/terraform/`)
- Update `main.tf` to export `local_sensitive_file` for `tls_private_key.auto_generated` to `deploy/digitalocean/terraform/id_ed25519`.
- Update `outputs.tf` to output:
  - `ssh_private_key_path`
  - `ansible_inventory_content`
  - `ansible_deploy_command` (e.g. `ansible-playbook -i deploy/ansible/inventory.ini deploy/ansible/playbook.yml --private-key deploy/digitalocean/terraform/id_ed25519`)

#### 3. Automated Deployment Runner Bridge (`deploy/digitalocean/scripts/deploy.sh`)
- After applying Terraform:
  - Export the SSH private key (if auto-generated) with `chmod 600`.
  - Dynamically write `deploy/ansible/inventory.ini` containing Droplet public IP, `ansible_user=deploy`, and private key path.
  - Automatically execute `ansible-playbook -i deploy/ansible/inventory.ini deploy/ansible/playbook.yml` (unless `--skip-ansible` or `--plan-only` is passed).
  - Print clear next steps, SSH commands, and update instructions.

#### 4. Ansible Playbook & Roles Upgrade (`deploy/ansible/`)
- **`roles/application/tasks/main.yml`**:
  - Template `.env` with DB credentials and Django secret key.
  - Synchronize monorepo code to `/opt/adventuretogether/`.
  - Install `/opt/adventuretogether/deploy/update.sh` on remote host with execute permissions.
  - Run `docker compose build` and start containers via systemd unit `adventuretogether.service`.
  - Execute database migrations inside running container.
  - Verify `/api/health/` returns HTTP 200.
- **`deploy/ansible/update.yml`**:
  - Dedicated update playbook for zero-downtime updates and migrations.

#### 5. Application Update Scripts (`deploy/digitalocean/scripts/update.sh` & `deploy/update.sh`)
- **`deploy/update.sh` (Remote Runner)**:
  - Navigates to `/opt/adventuretogether/deploy`.
  - Pulls latest git commits from `origin/main` (or syncs workspace).
  - Runs `docker compose build --pull`.
  - Runs `docker compose up -d --no-deps db` and waits for PostgreSQL healthcheck.
  - Runs `docker compose run --rm backend python manage.py migrate --noinput`.
  - Runs `docker compose run --rm backend python manage.py collectstatic --noinput`.
  - Runs `docker compose up -d --remove-orphans`.
  - Validates `curl -f http://localhost/api/health/`.
- **`deploy/digitalocean/scripts/update.sh` (Local Runner)**:
  - Reads IP and SSH key from Terraform/Ansible inventory.
  - Connects over SSH to trigger `/opt/adventuretogether/deploy/update.sh`.

---

### File Structure
```
deploy/
├── ansible/
│   ├── inventory.ini                     # Managed Ansible inventory with Droplet IP & SSH key
│   ├── playbook.yml                      # Full provisioning and deployment playbook
│   ├── update.yml                        # Dedicated application update and migration playbook
│   └── roles/
│       ├── application/tasks/main.yml    # Code sync, .env templating, build, migrate, service
│       ├── common/tasks/main.yml         # Base packages and deploy user setup
│       ├── postgres/tasks/main.yml       # PostGIS backup script and cron
│       └── security/tasks/main.yml       # UFW firewall and Fail2ban configuration
├── digitalocean/
│   ├── scripts/
│   │   ├── deploy.sh                     # Automated Terraform -> Key/Inventory -> Ansible runner
│   │   ├── destroy.sh                    # Teardown script
│   │   └── update.sh                     # Local 1-command update runner over SSH
│   └── terraform/
│       ├── main.tf                       # Droplet, VPC, Firewall, Keypair, local key file
│       ├── outputs.tf                    # Droplet IP, SSH commands, Ansible commands
│       ├── templates/
│       │   └── cloud-init.yaml.tftpl     # Hardened bootstrap without host Nginx conflicts
│       └── variables.tf
├── docker-compose.yml                    # Production compose configuration
└── update.sh                             # Remote on-Droplet update & migration runner
```

---

### Architecture Diagram

```mermaid
graph LR
  subgraph Local Workstation
    A[deploy.sh / Terraform] -->|1. Provision VM| B[DigitalOcean Droplet]
    A -->|2. Export Key & Inventory| C[inventory.ini & id_ed25519]
    C -->|3. Auto-Trigger Ansible| D[ansible-playbook playbook.yml]
    E[update.sh CLI] -->|Update Trigger| D2[ansible-playbook update.yml / SSH]
  end

  subgraph DigitalOcean Droplet
    B --> F[Cloud-Init Bootstrap: Swap, Docker, UFW]
    D -->|Deploy Code & .env| G[/opt/adventuretogether]
    D2 -->|Git Pull & Rebuild| G
    G --> H[docker compose up -d]
    H --> I[PostGIS Database Container]
    H --> J[Django Backend Container]
    H --> K[Django-Q2 Worker Container]
    H --> L[Vue 3 / Nginx Frontend Container]
    G -->|Execute Migrations| M[manage.py migrate]
    M -->|Schema Updates| I
    I -->|Preserved Data Volume| N[(postgis_data)]
  end
```

---

### Risks & Mitigations
- **Risk: Host Nginx Re-activation**: If an external script installs `nginx`, port 80 could be seized.
  - *Mitigation*: Cloud-Init and Ansible explicitly disable and mask the host `nginx` service.
- **Risk: Failed Migration during Update**: A bad migration could leave the backend in a broken state.
  - *Mitigation*: `update.sh` runs migrations in an isolated container (`docker compose run --rm backend python manage.py migrate`) before reloading the main backend service. If migration fails, the update halts and existing containers continue running.
- **Risk: Data Volume Deletion**: Running `docker compose down -v` could wipe PostGIS data.
  - *Mitigation*: Update scripts strictly use `docker compose up -d --remove-orphans` and never pass `-v` (volumes flag). Automated daily backups to `/var/backups/adventuretogether` provide an extra safety net.

# Testing

### Validation Approach
Automated testing and verification will be performed across three layers:
1. **IaC & Configuration Syntax Testing**: Pytest suite checking Terraform schema validity, Cloud-Init YAML parsing without unresolved variables, and Ansible playbook linting/syntax.
2. **Script Execution & Argument Testing**: Automated tests verifying CLI flag parsing, path handling, and help text in `deploy.sh` and `update.sh`.
3. **End-to-End Health Check Simulation**: Testing the migration command sequence and API health check endpoint contract (`/api/health/`).

---

### Key Scenarios
1. **Fresh Provisioning & Ansible Bridge**:
   - Execute `deploy.sh` with test parameters / `--plan-only`.
   - Verify that `id_ed25519` key file is staged with `0600` permissions.
   - Verify that `deploy/ansible/inventory.ini` is generated with valid host syntax, matching user `deploy` and key path.
   - Verify that Ansible playbook syntax checks pass with `ansible-playbook --syntax-check`.
2. **Application Update Workflow**:
   - Execute `update.sh` in dry-run/mock mode.
   - Verify that the execution order is: Git pull -> Docker build -> Isolated Migration -> Static Collection -> Service Reload -> Health Check.
   - Verify that persistent volume `postgis_data` is untouched.
3. **Migration Failure Handling**:
   - Verify that if `python manage.py migrate` fails (non-zero exit code), the update script halts before restarting production containers and reports actionable error diagnostics.

---

### Edge Cases
- **Missing Local SSH Key**: If the user provides no key, Terraform generates one, saves it to disk, and Ansible uses it seamlessly.
- **Custom Domain vs Direct IP**: Both Cloud-Init and Ansible properly populate `DJANGO_ALLOWED_HOSTS` with the direct IP, domain, and localhost.
- **Host Nginx Pre-installation**: Cloud-Init ensures host Nginx is stopped and disabled so port 80/443 remain available for Docker.

---

### Test Changes
- **Update `backend/apps/core/test_deployment_templates.py`**:
  - Add `test_cloud_init_does_not_contain_host_nginx_package`
  - Add `test_ansible_playbook_syntax_and_roles`
  - Add `test_ansible_inventory_template`
  - Add `test_update_scripts_exist_and_executable`
  - Add `test_update_script_migration_sequence`

# Delivery Steps

### ✓ Step 1: Resolve Host Nginx Conflicts and Enhance Terraform/Cloud-Init Key Automation
The Terraform and Cloud-Init templates eliminate host-level port conflicts, automatically persist generated SSH private keys to disk, and export dynamic Ansible inventory files.

- Update `deploy/digitalocean/terraform/templates/cloud-init.yaml.tftpl` to remove conflicting host packages (`python3-certbot-nginx` which auto-starts host Nginx on port 80) and ensure host ports 80/443 are reserved exclusively for the containerized frontend reverse proxy.
- Update `deploy/digitalocean/terraform/outputs.tf` and `main.tf` to export dedicated Ansible connection strings, host variables, and an automated local private key file (`deploy/digitalocean/terraform/id_ed25519`).
- Enhance `deploy/digitalocean/scripts/deploy.sh` to extract the SSH key, generate `deploy/ansible/inventory.ini`, and print exact copy-pasteable SSH and Ansible commands.

### ✓ Step 2: Upgrade Ansible Roles for Full Application Deployment and Migrations
The Ansible playbooks and roles fully orchestrate containerized application deployment, production environment variables, and automated database migrations.

- Update `deploy/ansible/roles/application/tasks/main.yml` to template `/opt/adventuretogether/deploy/.env` with production secrets, synchronize application source code, and trigger `docker compose up -d --build`.
- Add an automated task in Ansible to execute `docker compose exec -T backend python manage.py migrate --noinput` and `docker compose exec -T backend python manage.py collectstatic --noinput` on initial deploy.
- Update `deploy/ansible/inventory.ini` and `deploy/ansible/playbook.yml` to provide turnkey execution against the provisioned Droplet IP using the dedicated `deploy` user.
- Connect `deploy/digitalocean/scripts/deploy.sh` to automatically run Ansible upon successful infrastructure provisioning unless `--skip-ansible` is specified.

### ✓ Step 3: Implement Dual Local and Remote Update Scripts with Zero-Data-Loss Migrations
Engineers and CI/CD pipelines can update the running application to match the latest `main` git branch and execute database migrations with zero state reset.

- Implement local update script `deploy/digitalocean/scripts/update.sh` that connects over SSH to pull the latest code, build updated Docker images, run Django migrations, reload services, and verify health checks.
- Implement remote on-Droplet update script `deploy/update.sh` (installed to `/opt/adventuretogether/deploy/update.sh`) for direct host execution or webhook triggers.
- Create dedicated Ansible update playbook `deploy/ansible/update.yml` that performs rolling container updates and database schema migrations without touching persistent PostGIS volumes (`postgis_data`).
- Add container health check verification against `/api/health/` with automated rollback guidance in case of container start failures.

### ✓ Step 4: Add Automated Test Coverage and Comprehensive Operational Documentation
The deployment test suite validates all IaC/Ansible templates and update scripts, and the documentation repository contains complete operational guides.

- Extend `backend/apps/core/test_deployment_templates.py` with test cases verifying Cloud-Init YAML validity, Ansible playbook syntax, inventory generation, and update script argument handling.
- Update `documentation/digitalocean_deployment.md` and `documentation/deployment_guide.md` with step-by-step guides, exact Ansible commands, SSH key locations, update workflows, and disaster recovery procedures.
- Update `FEATURES.md` with **FEAT-012** capturing the automated deployment bridge, dual update pathways, and state-preserving database migrations.
- Author completed summary report in `.junie/reports/` documenting prompt interpretation and architecture delivery.