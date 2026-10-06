# AdventureTogether - Infrastructure & Deployment Guide

This guide provides step-by-step instructions for running AdventureTogether in local development, containerized production environments, and provisioning production virtual machines using Ansible.

---

## 1. System Architecture

```
[ Nginx Web Server (Port 80) ]
        │
        ├──> [ / : Single Vue 3 SPA (Vite, Pinia, Scoped CSS) ]
        │
        └──> [ /api/* : Django REST API + GeoDjango (Port 8000) ]
                    │
                    ├──> [ PostgreSQL 16 + PostGIS 3.4 (Port 5432) ]
                    │           ▲
                    │           │ (ORM Broker)
                    └──> [ Django-Q2 Harvester Worker ]
```

**Key Architectural Features**:
- **Zero-Redis Stack**: Task queuing (Django-Q2) and location temporal decay run directly on PostgreSQL/PostGIS, minimizing RAM footprint.
- **Code-Split Vue SPA**: Host management modules are lazy-loaded on demand to ensure minimal initial payload for field participants on mobile devices.

---

## 2. Local Development Setup

### Prerequisites
- Python 3.12+ with GDAL & SpatiaLite installed
- Node.js 18+ and npm

### 2.1 Backend Setup
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

### 2.2 Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
The Vite development server runs at `http://localhost:3000` with automated proxying to the Django backend.

---

## 3. Production Docker Deployment

Deploy the full containerized stack using Docker Compose:
```bash
docker compose up -d --build
```

### Container Registry:
1. `adventure_together_db`: PostGIS 16-3.4 spatial database with persistent volume `postgis_data`.
2. `adventure_together_backend`: Django REST API with GeoDjango.
3. `adventure_together_worker`: Background Harvester worker running `python manage.py qcluster`.
4. `adventure_together_frontend`: Vue 3 SPA served via optimized Nginx with Gzip compression.

---

## 4. Production VM Provisioning with Ansible

The playbooks in `deploy/ansible/` configure an Ubuntu/Debian server from scratch with non-root execution, UFW firewall rules, Fail2ban protection, and daily automated PostGIS backups.

### Running Ansible Playbook
```bash
cd deploy/ansible
ansible-playbook -i inventory.ini playbook.yml
```

### Automated Backup & Disaster Recovery
- **Daily Cron Backup**: Runs at 02:00 UTC, outputting to `/var/backups/adventuretogether/postgis_backup_<timestamp>.sql.gz`.
- **Retention**: Automatically purges backups older than 14 days.
- **Restore Command**:
```bash
gunzip < /var/backups/adventuretogether/postgis_backup_<timestamp>.sql.gz | docker exec -i adventure_together_db psql -U postgres -d adventure_together
```
