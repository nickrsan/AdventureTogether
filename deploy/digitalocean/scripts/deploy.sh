#!/usr/bin/env bash
# ==============================================================================
# AdventureTogether - DigitalOcean Automated Deployment Runner
# ==============================================================================
# This script automates zero-to-deployed provisioning on DigitalOcean using
# Terraform / OpenTofu. It validates credentials, prepares variable definitions,
# runs pre-flight syntax checks, and applies infrastructure changes.
#
# Usage:
#   ./deploy.sh --token "<DO_API_TOKEN>" [options]
#
# Options:
#   --token, -t        DigitalOcean Personal Access Token (or set DIGITALOCEAN_TOKEN)
#   --region, -r       Region slug (default: sfo3)
#   --domain, -d       Optional domain name (e.g. adventure.example.com)
#   --ip, -i           Optional existing Reserved IPv4 address to bind
#   --allocate-ip      Flag to allocate a new static Reserved IPv4 address in the target region
#   --size, -s         Droplet plan slug (default: s-2vcpu-4gb)
#   --ssh-key, -k      Optional SSH public key file or string
#   --env, -e          Environment name (default: production)
#   --auto-approve     Skip interactive confirmation prompt
#   --plan-only        Generate and display execution plan without applying
#   --skip-ansible     Skip automated Ansible playbook execution after provisioning
#   --help, -h         Show this help message
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="${SCRIPT_DIR}/../terraform"
ANSIBLE_DIR="${SCRIPT_DIR}/../../ansible"

# Default configuration parameters
DO_TOKEN="${DIGITALOCEAN_TOKEN:-${DO_TOKEN:-}}"
REGION="sfo3"
DOMAIN=""
RESERVED_IP=""
ALLOCATE_IP="false"
DROPLET_SIZE="s-2vcpu-4gb"
SSH_PUBLIC_KEY=""
ENVIRONMENT="production"
AUTO_APPROVE="false"
PLAN_ONLY="false"
SKIP_ANSIBLE="false"

# Parse CLI arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --token|-t)
      DO_TOKEN="$2"
      shift 2
      ;;
    --region|-r)
      REGION="$2"
      shift 2
      ;;
    --domain|-d)
      DOMAIN="$2"
      shift 2
      ;;
    --ip|-i)
      RESERVED_IP="$2"
      shift 2
      ;;
    --allocate-ip)
      ALLOCATE_IP="true"
      shift 1
      ;;
    --size|-s)
      DROPLET_SIZE="$2"
      shift 2
      ;;
    --ssh-key|-k)
      if [ -f "$2" ]; then
        SSH_PUBLIC_KEY="$(cat "$2")"
      else
        SSH_PUBLIC_KEY="$2"
      fi
      shift 2
      ;;
    --env|-e)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --auto-approve)
      AUTO_APPROVE="true"
      shift 1
      ;;
    --plan-only)
      PLAN_ONLY="true"
      shift 1
      ;;
    --skip-ansible)
      SKIP_ANSIBLE="true"
      shift 1
      ;;
    --help|-h)
      head -n 25 "$0" | tail -n +3 | sed 's/^# //'
      exit 0
      ;;
    *)
      echo "Error: Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

echo "========================================================================"
echo "    AdventureTogether - DigitalOcean Zero-to-Deployed Provisioner       "
echo "========================================================================"

# Validation of required parameters
if [ -z "${DO_TOKEN}" ]; then
  echo "Error: DigitalOcean API Token is required." >&2
  echo "Supply via --token flag or DIGITALOCEAN_TOKEN environment variable." >&2
  exit 1
fi

# Detect IaC binary (tofu or terraform)
IAC_BIN=""
if command -v tofu >/dev/null 2>&1; then
  IAC_BIN="tofu"
elif command -v terraform >/dev/null 2>&1; then
  IAC_BIN="terraform"
elif [ -x "$HOME/.local/bin/tofu" ]; then
  IAC_BIN="$HOME/.local/bin/tofu"
elif [ -x "$HOME/.local/bin/terraform" ]; then
  IAC_BIN="$HOME/.local/bin/terraform"
else
  echo "Error: Neither OpenTofu ('tofu') nor Terraform ('terraform') is installed in PATH." >&2
  exit 1
fi

echo "Using IaC Engine : ${IAC_BIN} ($(${IAC_BIN} version | head -n 1))"
echo "Target Region    : ${REGION}"
echo "Environment      : ${ENVIRONMENT}"
echo "Droplet Size     : ${DROPLET_SIZE}"
if [ -n "${RESERVED_IP}" ]; then
  echo "Binding IPv4     : ${RESERVED_IP} (Pre-existing Reserved IP)"
elif [ "${ALLOCATE_IP}" = "true" ]; then
  echo "Binding IPv4     : Fresh static Reserved IPv4 allocation requested"
else
  echo "Binding IPv4     : Dynamic Droplet public IPv4"
fi

if [ -n "${DOMAIN}" ]; then
  echo "Configuring Domain: ${DOMAIN} (DigitalOcean DNS & Let's Encrypt TLS)"
fi
echo "========================================================================"

cd "${TF_DIR}"

# Initialize Terraform/OpenTofu
echo "[1/4] Initializing provider plugins..."
"${IAC_BIN}" init -upgrade

# Validate templates
echo "[2/4] Validating infrastructure templates..."
"${IAC_BIN}" validate

# Build terraform variable arguments
TF_VARS=(
  -var="do_token=${DO_TOKEN}"
  -var="region=${REGION}"
  -var="environment=${ENVIRONMENT}"
  -var="droplet_size=${DROPLET_SIZE}"
)

if [ -n "${DOMAIN}" ]; then
  TF_VARS+=(-var="domain_name=${DOMAIN}" -var="create_dns_records=true")
fi

if [ -n "${RESERVED_IP}" ]; then
  TF_VARS+=(-var="existing_reserved_ipv4=${RESERVED_IP}")
fi

if [ "${ALLOCATE_IP}" = "true" ]; then
  TF_VARS+=(-var="allocate_reserved_ipv4=true")
fi

if [ -n "${SSH_PUBLIC_KEY}" ]; then
  TF_VARS+=(-var="ssh_public_key=${SSH_PUBLIC_KEY}")
fi

if [ "${PLAN_ONLY}" = "true" ]; then
  echo "[3/4] Generating plan..."
  "${IAC_BIN}" plan "${TF_VARS[@]}"
  echo "[4/4] Plan completed. Skipping apply because --plan-only was specified."
  exit 0
fi

echo "[3/4] Applying infrastructure changes..."
if [ "${AUTO_APPROVE}" = "true" ]; then
  "${IAC_BIN}" apply -auto-approve "${TF_VARS[@]}"
else
  "${IAC_BIN}" apply "${TF_VARS[@]}"
fi

echo "========================================================================"
echo "[4/5] Infrastructure Provisioning Complete!"
echo "Outputs:"
"${IAC_BIN}" output

EFFECTIVE_IP="$("${IAC_BIN}" output -raw effective_public_ipv4 2>/dev/null || echo "")"
SSH_KEY_FILE="${TF_DIR}/id_ed25519"

# If an auto-generated private key was written by Terraform, ensure 0600 permissions
if [ -f "${SSH_KEY_FILE}" ]; then
  chmod 600 "${SSH_KEY_FILE}"
fi

# Determine private key file for Ansible inventory
if [ -n "${SSH_PUBLIC_KEY}" ] && [ -f "${SSH_PUBLIC_KEY}" ]; then
  PRIV_CANDIDATE="${SSH_PUBLIC_KEY%.pub}"
  if [ -f "${PRIV_CANDIDATE}" ]; then
    ANSIBLE_KEY_PATH="${PRIV_CANDIDATE}"
  else
    ANSIBLE_KEY_PATH="~/.ssh/id_rsa"
  fi
elif [ -f "${SSH_KEY_FILE}" ]; then
  ANSIBLE_KEY_PATH="${SSH_KEY_FILE}"
else
  ANSIBLE_KEY_PATH="~/.ssh/id_rsa"
fi

# Generate deploy/ansible/inventory.ini dynamically
if [ -n "${EFFECTIVE_IP}" ]; then
  echo ""
  echo "Generating dynamic Ansible inventory at ${ANSIBLE_DIR}/inventory.ini..."
  mkdir -p "${ANSIBLE_DIR}"
  cat << EOF > "${ANSIBLE_DIR}/inventory.ini"
[app_servers]
droplet ansible_host=${EFFECTIVE_IP} ansible_user=deploy ansible_ssh_private_key_file=${ANSIBLE_KEY_PATH}
EOF
  echo "Ansible inventory successfully generated."
fi

# Run Ansible if requested and available
echo "========================================================================"
if [ "${SKIP_ANSIBLE}" = "false" ]; then
  echo "[5/5] Executing Ansible Application Deployment..."
  if command -v ansible-playbook >/dev/null 2>&1; then
    echo "Running: ansible-playbook -i ${ANSIBLE_DIR}/inventory.ini ${ANSIBLE_DIR}/playbook.yml"
    ansible-playbook -i "${ANSIBLE_DIR}/inventory.ini" "${ANSIBLE_DIR}/playbook.yml"
  else
    echo "Notice: 'ansible-playbook' CLI is not found on your local workstation."
    echo "To run deployment manually once Ansible is installed, execute:"
    echo "  ansible-playbook -i ${ANSIBLE_DIR}/inventory.ini ${ANSIBLE_DIR}/playbook.yml"
  fi
else
  echo "[5/5] Skipping Ansible playbook execution (--skip-ansible specified)."
fi

echo "========================================================================"
echo "Deployment Summary & Next Steps:"
if [ -n "${EFFECTIVE_IP}" ]; then
  echo "  - Web App URL       : http://${EFFECTIVE_IP}"
  echo "  - API Health Check  : http://${EFFECTIVE_IP}/api/health/"
  echo "  - Direct SSH Command: ssh -i ${ANSIBLE_KEY_PATH} deploy@${EFFECTIVE_IP}"
  echo "  - Ansible Playbook  : ansible-playbook -i ${ANSIBLE_DIR}/inventory.ini ${ANSIBLE_DIR}/playbook.yml"
fi
echo "========================================================================"
