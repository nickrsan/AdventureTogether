"""
Unit and integration tests for DigitalOcean deployment templates and infrastructure.

Validates Terraform / OpenTofu configuration, Cloud-Init templating,
App Platform spec schema, and deployment scripts.
"""

import os
import subprocess
import shutil
from pathlib import Path
import pytest
import yaml

# Base project paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DEPLOY_DIR = BASE_DIR / "deploy"
DEPLOY_DO_DIR = DEPLOY_DIR / "digitalocean"
ANSIBLE_DIR = DEPLOY_DIR / "ansible"
TERRAFORM_DIR = DEPLOY_DO_DIR / "terraform"
APP_PLATFORM_SPEC = DEPLOY_DO_DIR / "app-platform" / "app.yaml"
DEPLOY_SCRIPT = DEPLOY_DO_DIR / "scripts" / "deploy.sh"
DESTROY_SCRIPT = DEPLOY_DO_DIR / "scripts" / "destroy.sh"
LOCAL_UPDATE_SCRIPT = DEPLOY_DO_DIR / "scripts" / "update.sh"
REMOTE_UPDATE_SCRIPT = DEPLOY_DIR / "update.sh"


class TestTerraformTemplates:
    """Tests for DigitalOcean Terraform / OpenTofu infrastructure templates."""

    def test_terraform_files_exist(self):
        """Ensure all required Terraform and template files are present."""
        assert (TERRAFORM_DIR / "versions.tf").is_file()
        assert (TERRAFORM_DIR / "main.tf").is_file()
        assert (TERRAFORM_DIR / "variables.tf").is_file()
        assert (TERRAFORM_DIR / "outputs.tf").is_file()
        assert (TERRAFORM_DIR / "terraform.tfvars.example").is_file()
        assert (TERRAFORM_DIR / "templates" / "cloud-init.yaml.tftpl").is_file()

    def test_terraform_opentofu_validation(self):
        """Run tofu validate / terraform validate to check HCL syntax and provider schemas."""
        iac_bin = shutil.which("tofu") or shutil.which("terraform") or str(Path.home() / ".local" / "bin" / "tofu")
        if not iac_bin or not os.path.exists(iac_bin):
            pytest.skip("Neither OpenTofu nor Terraform CLI binary is installed in environment.")

        # Ensure directory is initialized
        init_res = subprocess.run(
            [iac_bin, "init", "-backend=false"],
            cwd=str(TERRAFORM_DIR),
            capture_output=True,
            text=True
        )
        assert init_res.returncode == 0, f"Terraform init failed:\n{init_res.stderr}"

        # Validate configuration
        val_res = subprocess.run(
            [iac_bin, "validate"],
            cwd=str(TERRAFORM_DIR),
            capture_output=True,
            text=True
        )
        assert val_res.returncode == 0, f"Terraform validate failed:\n{val_res.stderr}\n{val_res.stdout}"

    def test_cloud_init_template_syntax_and_substitutions(self):
        """Verify that the cloud-init template renders properly with sample variables and produces valid YAML."""
        template_file = TERRAFORM_DIR / "templates" / "cloud-init.yaml.tftpl"
        content = template_file.read_text()

        # Mock variable substitutions matching Terraform templatefile
        sample_vars = {
            "${ssh_public_key}": "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestKey deploy@test",
            "${git_repository_url}": "https://github.com/AdventureTogether/AdventureTogether.git",
            "${git_branch}": "main",
            "${django_debug}": "False",
            "${django_secret_key}": "test-super-secret-key-12345",
            "${django_allowed_hosts}": "localhost,127.0.0.1,adventure.example.com",
            "${django_q_workers}": "4",
            "${postgres_db_name}": "adventure_together",
            "${postgres_user}": "postgres",
            "${postgres_password}": "test-postgres-password",
            "${domain_name}": "adventure.example.com",
            "${admin_email}": "admin@adventure.example.com",
            "$${BACKUP_DIR}": "${BACKUP_DIR}",
            "$${DATE}": "${DATE}",
            "$${BACKUP_FILE}": "${BACKUP_FILE}",
        }

        rendered = content
        for var_pattern, val in sample_vars.items():
            rendered = rendered.replace(var_pattern, str(val))

        # Check that no unresolved unescaped ${...} variables remain
        assert "${django_secret_key}" not in rendered
        assert "${postgres_db_name}" not in rendered

        # Parse YAML to verify validity
        parsed = yaml.safe_load(rendered)
        assert isinstance(parsed, dict)
        assert "package_update" in parsed
        assert "packages" in parsed
        assert "docker.io" in parsed["packages"]
        assert "docker-compose-v2" in parsed["packages"]
        assert "write_files" in parsed

        # Check swapfile configuration
        assert "swap" in parsed
        assert parsed["swap"]["filename"] == "/swapfile"
        assert parsed["swap"]["size"] == 2147483648

        # Check write_files contents
        paths = [f["path"] for f in parsed["write_files"]]
        assert "/etc/fail2ban/jail.local" in paths
        assert "/usr/local/bin/backup_postgis.sh" in paths
        assert "/etc/systemd/system/adventuretogether.service" in paths
        assert "/root/bootstrap_adventuretogether.sh" in paths

    def test_terraform_sfo_region_and_droplet_sizing_defaults(self):
        """Validate that Terraform variables default to SFO region (sfo3) and s-2vcpu-4gb sizing."""
        variables_content = (TERRAFORM_DIR / "variables.tf").read_text()
        assert 'default     = "sfo3"' in variables_content
        assert 'default     = "s-2vcpu-4gb"' in variables_content
        assert "s-4vcpu-8gb" in variables_content
        assert "s-2vcpu-2gb" in variables_content

        tfvars_content = (TERRAFORM_DIR / "terraform.tfvars.example").read_text()
        assert 'region = "sfo3"' in tfvars_content

    def test_terraform_main_droplet_and_firewall_wiring(self):
        """Verify main.tf configures droplet monitoring, backups, and firewall rules."""
        main_content = (TERRAFORM_DIR / "main.tf").read_text()
        assert "digitalocean_vpc" in main_content
        assert "digitalocean_droplet" in main_content
        assert "digitalocean_firewall" in main_content
        assert "digitalocean_reserved_ip" in main_content
        assert "backups    = true" in main_content
        assert "monitoring = true" in main_content
        assert "local_sensitive_file" in main_content

    def test_cloud_init_does_not_contain_host_nginx_package(self):
        """Verify Cloud-Init package list excludes conflicting python3-certbot-nginx host package."""
        template_file = TERRAFORM_DIR / "templates" / "cloud-init.yaml.tftpl"
        content = template_file.read_text()
        parsed = yaml.safe_load(content)
        packages = parsed.get("packages", [])
        assert "python3-certbot-nginx" not in packages
        assert "nginx" not in packages

    def test_cloud_init_contains_host_nginx_disabling_and_migrations(self):
        """Verify Cloud-Init bootstrap disables host Nginx and executes Django migrations."""
        template_file = TERRAFORM_DIR / "templates" / "cloud-init.yaml.tftpl"
        content = template_file.read_text()
        assert "systemctl stop nginx" in content
        assert "systemctl disable nginx" in content
        assert "systemctl mask nginx" in content
        assert "python manage.py migrate --noinput" in content
        assert "python manage.py collectstatic --noinput" in content
        assert "chmod +x /opt/adventuretogether/deploy/update.sh" in content

    def test_terraform_ssh_key_persistence_and_ansible_outputs(self):
        """Verify Terraform outputs expose SSH key path and Ansible inventory/deploy commands."""
        outputs_content = (TERRAFORM_DIR / "outputs.tf").read_text()
        assert "output \"ssh_private_key_path\"" in outputs_content
        assert "output \"ansible_inventory_content\"" in outputs_content
        assert "output \"ansible_deploy_command\"" in outputs_content
        assert "id_ed25519" in outputs_content
        assert "deploy/ansible/inventory.ini" in outputs_content


class TestAnsiblePlaybooksAndRoles:
    """Tests for Ansible playbooks, inventory configuration, and role tasks."""

    def test_ansible_files_exist(self):
        """Ensure all required Ansible playbooks, inventories, and role task files exist."""
        assert (ANSIBLE_DIR / "playbook.yml").is_file()
        assert (ANSIBLE_DIR / "update.yml").is_file()
        assert (ANSIBLE_DIR / "inventory.ini").is_file()
        assert (ANSIBLE_DIR / "roles" / "common" / "tasks" / "main.yml").is_file()
        assert (ANSIBLE_DIR / "roles" / "security" / "tasks" / "main.yml").is_file()
        assert (ANSIBLE_DIR / "roles" / "postgres" / "tasks" / "main.yml").is_file()
        assert (ANSIBLE_DIR / "roles" / "application" / "tasks" / "main.yml").is_file()

    def test_ansible_playbooks_yaml_validity(self):
        """Validate YAML syntax for Ansible provision and update playbooks."""
        for playbook_file in ["playbook.yml", "update.yml"]:
            content = (ANSIBLE_DIR / playbook_file).read_text()
            data = yaml.safe_load(content)
            assert isinstance(data, list)
            assert len(data) >= 1
            assert "hosts" in data[0]

    def test_ansible_roles_yaml_validity(self):
        """Validate YAML syntax for all role task files."""
        for role_name in ["common", "security", "postgres", "application"]:
            role_file = ANSIBLE_DIR / "roles" / role_name / "tasks" / "main.yml"
            content = role_file.read_text()
            data = yaml.safe_load(content)
            assert isinstance(data, list)
            assert len(data) >= 1

    def test_ansible_application_tasks_contain_migrations_and_env(self):
        """Verify application role manages .env templating, database migrations, and health checks."""
        app_tasks = (ANSIBLE_DIR / "roles" / "application" / "tasks" / "main.yml").read_text()
        assert "{{ project_root }}/deploy/.env" in app_tasks
        assert "python manage.py migrate --noinput" in app_tasks
        assert "python manage.py collectstatic --noinput" in app_tasks
        assert "http://127.0.0.1/api/health/" in app_tasks
        assert "adventuretogether.service" in app_tasks

    def test_ansible_security_tasks_mask_host_nginx(self):
        """Verify security role masks host Nginx service to prevent port conflicts."""
        sec_tasks = (ANSIBLE_DIR / "roles" / "security" / "tasks" / "main.yml").read_text()
        assert "name: nginx" in sec_tasks
        assert "state: stopped" in sec_tasks
        assert "masked: yes" in sec_tasks

    def test_ansible_inventory_groups_and_vars(self):
        """Verify inventory.ini contains standard host groups and shared variables."""
        inventory_content = (ANSIBLE_DIR / "inventory.ini").read_text()
        assert "[app_servers]" in inventory_content
        assert "[scavenger_servers]" in inventory_content
        assert "[app_servers:vars]" in inventory_content
        assert "ansible_python_interpreter" in inventory_content
        assert "postgres_db" in inventory_content


class TestAppPlatformSpec:
    """Tests for DigitalOcean App Platform declarative specification."""

    def test_app_spec_exists_and_is_valid_yaml(self):
        """Ensure app.yaml exists and parses cleanly as YAML."""
        assert APP_PLATFORM_SPEC.is_file()
        spec_content = APP_PLATFORM_SPEC.read_text()
        spec = yaml.safe_load(spec_content)
        assert isinstance(spec, dict)

    def test_app_spec_services_and_databases(self):
        """Validate required App Platform service components, databases, and routes."""
        spec = yaml.safe_load(APP_PLATFORM_SPEC.read_text())

        assert spec.get("name") == "adventuretogether"
        assert "databases" in spec
        assert any(db["name"] == "db" and db["engine"] == "PG" for db in spec["databases"])

        services = {s["name"]: s for s in spec.get("services", [])}
        assert "backend" in services
        assert "frontend" in services

        # Backend service checks
        backend = services["backend"]
        assert backend["http_port"] == 8000
        assert backend.get("health_check", {}).get("http_path") == "/api/health/"
        env_keys = [e["key"] for e in backend.get("envs", [])]
        assert "POSTGRES_DB" in env_keys
        assert "DJANGO_SECRET_KEY" in env_keys

        # Frontend service checks
        frontend = services["frontend"]
        assert frontend["http_port"] == 80

        # Background worker checks
        workers = {w["name"]: w for w in spec.get("workers", [])}
        assert "worker" in workers
        assert "qcluster" in workers["worker"]["run_command"]


class TestDeploymentScripts:
    """Tests for automated deployment runner scripts."""

    def test_scripts_executable(self):
        """Verify deployment runner scripts have executable permissions."""
        assert os.access(DEPLOY_SCRIPT, os.X_OK)
        assert os.access(DESTROY_SCRIPT, os.X_OK)

    def test_deploy_script_help(self):
        """Verify ./deploy.sh --help executes cleanly and displays usage."""
        res = subprocess.run(
            [str(DEPLOY_SCRIPT), "--help"],
            capture_output=True,
            text=True
        )
        assert res.returncode == 0
        assert "AdventureTogether - DigitalOcean Zero-to-Deployed Provisioner" in res.stdout or "AdventureTogether" in res.stdout
        assert "--token" in res.stdout
        assert "--region" in res.stdout
        assert "sfo3" in res.stdout
        assert "s-2vcpu-4gb" in res.stdout
        assert "--domain" in res.stdout
        assert "--ip" in res.stdout
        assert "--skip-ansible" in res.stdout

    def test_destroy_script_help(self):
        """Verify ./destroy.sh --help executes cleanly and displays usage."""
        res = subprocess.run(
            [str(DESTROY_SCRIPT), "--help"],
            capture_output=True,
            text=True
        )
        assert res.returncode == 0
        assert "Usage: ./destroy.sh" in res.stdout
        assert "--token" in res.stdout

    def test_deploy_script_requires_token(self):
        """Verify ./deploy.sh fails with an error if no API token is provided."""
        res = subprocess.run(
            [str(DEPLOY_SCRIPT)],
            capture_output=True,
            text=True,
            env={k: v for k, v in os.environ.items() if k not in ("DO_TOKEN", "DIGITALOCEAN_TOKEN")}
        )
        assert res.returncode != 0
        assert "DigitalOcean API Token is required" in res.stderr

    def test_deploy_script_contains_ansible_inventory_and_execution_logic(self):
        """Verify deploy.sh contains automated inventory generation and Ansible execution."""
        deploy_content = DEPLOY_SCRIPT.read_text()
        assert "inventory.ini" in deploy_content
        assert "ansible-playbook" in deploy_content
        assert "SKIP_ANSIBLE" in deploy_content
        assert "chmod 600" in deploy_content


class TestUpdateScripts:
    """Tests for application update scripts and zero-data-loss migration runners."""

    def test_update_scripts_exist_and_are_executable(self):
        """Verify remote and local update scripts exist with executable permissions."""
        assert REMOTE_UPDATE_SCRIPT.is_file()
        assert LOCAL_UPDATE_SCRIPT.is_file()
        assert os.access(REMOTE_UPDATE_SCRIPT, os.X_OK)
        assert os.access(LOCAL_UPDATE_SCRIPT, os.X_OK)

    def test_remote_update_script_help(self):
        """Verify deploy/update.sh --help executes cleanly and outputs expected options."""
        res = subprocess.run(
            [str(REMOTE_UPDATE_SCRIPT), "--help"],
            capture_output=True,
            text=True
        )
        assert res.returncode == 0
        assert "AdventureTogether - Remote On-Droplet Application Update & Migration Runner" in res.stdout
        assert "--branch" in res.stdout
        assert "--skip-pull" in res.stdout
        assert "--skip-migrations" in res.stdout
        assert "--dry-run" in res.stdout

    def test_remote_update_script_dry_run(self):
        """Verify deploy/update.sh --dry-run simulates the update sequence without executing commands."""
        res = subprocess.run(
            [str(REMOTE_UPDATE_SCRIPT), "--dry-run", "--skip-pull"],
            capture_output=True,
            text=True
        )
        assert res.returncode == 0
        assert "[DRY-RUN]" in res.stdout
        assert "docker compose" in res.stdout
        assert "migrate" in res.stdout
        assert "collectstatic" in res.stdout

    def test_remote_update_script_migration_safety(self):
        """Verify update.sh executes migrations in an isolated container and never destroys volumes."""
        content = REMOTE_UPDATE_SCRIPT.read_text()
        assert "docker compose" in content
        assert "python manage.py migrate --noinput" in content
        assert "python manage.py collectstatic --noinput" in content
        # Ensure destructive down -v (which would wipe postgis_data) is never used
        assert "down -v" not in content
        assert "--volumes" not in content

    def test_local_update_script_help(self):
        """Verify deploy/digitalocean/scripts/update.sh --help executes cleanly and outputs options."""
        res = subprocess.run(
            [str(LOCAL_UPDATE_SCRIPT), "--help"],
            capture_output=True,
            text=True
        )
        assert res.returncode == 0
        assert "AdventureTogether - Local DigitalOcean Droplet Update CLI Runner" in res.stdout
        assert "--ip" in res.stdout
        assert "--ssh-key" in res.stdout
        assert "--branch" in res.stdout
        assert "--method" in res.stdout
        assert "--dry-run" in res.stdout

    def test_local_update_script_dry_run_with_ip(self):
        """Verify local update.sh --dry-run simulates SSH command dispatch."""
        res = subprocess.run(
            [str(LOCAL_UPDATE_SCRIPT), "--ip", "192.0.2.1", "--dry-run"],
            capture_output=True,
            text=True
        )
        assert res.returncode == 0
        assert "[DRY-RUN]" in res.stdout
        assert "192.0.2.1" in res.stdout
        assert "/opt/adventuretogether/deploy/update.sh" in res.stdout

    def test_ansible_update_playbook_contains_migrations(self):
        """Verify update.yml performs migrations, static collection, and rolling container restart."""
        content = (ANSIBLE_DIR / "update.yml").read_text()
        assert "python manage.py migrate --noinput" in content
        assert "python manage.py collectstatic --noinput" in content
        assert "docker compose" in content
        assert "/api/health/" in content
