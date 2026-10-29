#!/usr/bin/env bash
# ==============================================================================
# AdventureTogether - Local DigitalOcean Droplet Update CLI Runner
# ==============================================================================
# This script triggers an application update on the remote DigitalOcean Droplet
# from your local workstation or CI/CD runner.
#
# It automatically resolves the Droplet IP and SSH private key from Terraform
# state or Ansible inventory, connects over SSH (or Ansible), pulls latest code,
# runs database migrations, and performs a graceful rolling restart of containers.
#
# Usage:
#   ./update.sh [options]
#
# Options:
#   --ip, -i <ip_address>   Droplet public IP address (auto-detected if omitted)
#   --ssh-key, -k <path>    Path to SSH private key (auto-detected if omitted)
#   --user, -u <username>   SSH username on Droplet (default: deploy)
#   --branch, -b <branch>   Git branch to deploy (default: main)
#   --method, -m <method>   Update method: 'ssh' or 'ansible' (default: ssh)
#   --dry-run               Display commands without executing them
#   --help, -h              Show this help message
# ==============================================================================

set -euo pipefail

# ------------------------------------------------------------------------------
# 1. Path & Parameter Resolution
# ------------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="${SCRIPT_DIR}/../terraform"
ANSIBLE_DIR="${SCRIPT_DIR}/../../ansible"

DROPLET_IP=""
SSH_KEY_PATH=""
SSH_USER="deploy"
GIT_BRANCH="main"
UPDATE_METHOD="ssh"
DRY_RUN="false"

# Parse CLI arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ip|-i)
      DROPLET_IP="$2"
      shift 2
      ;;
    --ssh-key|-k)
      SSH_KEY_PATH="$2"
      shift 2
      ;;
    --user|-u)
      SSH_USER="$2"
      shift 2
      ;;
    --branch|-b)
      GIT_BRANCH="$2"
      shift 2
      ;;
    --method|-m)
      UPDATE_METHOD="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN="true"
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
echo "    AdventureTogether - DigitalOcean Remote Stack Updater               "
echo "========================================================================"

# Auto-detect Droplet IP if not explicitly provided
if [ -z "${DROPLET_IP}" ]; then
  # 1. Check Ansible inventory
  if [ -f "${ANSIBLE_DIR}/inventory.ini" ]; then
    DETECTED_IP="$(grep -E "ansible_host=" "${ANSIBLE_DIR}/inventory.ini" | head -n 1 | sed -E 's/.*ansible_host=([^ ]+).*/\1/' || true)"
    if [ -n "${DETECTED_IP}" ] && [ "${DETECTED_IP}" != "localhost" ]; then
      DROPLET_IP="${DETECTED_IP}"
    fi
  fi

  # 2. Check Terraform / OpenTofu output if still empty
  if [ -z "${DROPLET_IP}" ] && [ -d "${TF_DIR}" ]; then
    IAC_BIN="tofu"
    if ! command -v tofu >/dev/null 2>&1; then
      IAC_BIN="terraform"
    fi
    if command -v "${IAC_BIN}" >/dev/null 2>&1; then
      TF_IP="$(cd "${TF_DIR}" && "${IAC_BIN}" output -raw effective_public_ipv4 2>/dev/null || true)"
      if [ -n "${TF_IP}" ] && [ "${TF_IP}" != "N/A" ]; then
        DROPLET_IP="${TF_IP}"
      fi
    fi
  fi
fi

# Auto-detect SSH Key path if not provided
if [ -z "${SSH_KEY_PATH}" ]; then
  if [ -f "${TF_DIR}/id_ed25519" ]; then
    SSH_KEY_PATH="${TF_DIR}/id_ed25519"
  elif [ -f "${ANSIBLE_DIR}/inventory.ini" ]; then
    DETECTED_KEY="$(grep -E "ansible_ssh_private_key_file=" "${ANSIBLE_DIR}/inventory.ini" | head -n 1 | sed -E 's/.*ansible_ssh_private_key_file=([^ ]+).*/\1/' || true)"
    if [ -n "${DETECTED_KEY}" ] && [ -f "${DETECTED_KEY}" ]; then
      SSH_KEY_PATH="${DETECTED_KEY}"
    fi
  fi

  if [ -z "${SSH_KEY_PATH}" ]; then
    SSH_KEY_PATH="${HOME}/.ssh/id_rsa"
  fi
fi

# Validate Droplet IP presence
if [ -z "${DROPLET_IP}" ]; then
  echo "Error: Could not automatically detect Droplet IP address." >&2
  echo "Please supply it explicitly via: ./update.sh --ip <DROPLET_IP>" >&2
  exit 1
fi

echo "Configuration:"
echo "  Droplet IP    : ${DROPLET_IP}"
echo "  SSH User      : ${SSH_USER}"
echo "  SSH Key File  : ${SSH_KEY_PATH}"
echo "  Target Branch : ${GIT_BRANCH}"
echo "  Update Method : ${UPDATE_METHOD}"
echo "  Dry Run Mode  : ${DRY_RUN}"
echo "========================================================================"

# ------------------------------------------------------------------------------
# 2. Execute Update Routine
# ------------------------------------------------------------------------------

if [ "${UPDATE_METHOD}" = "ssh" ]; then
  echo "Connecting via SSH to trigger remote update script..."
  SSH_CMD="ssh -i \"${SSH_KEY_PATH}\" -o StrictHostKeyChecking=accept-new \"${SSH_USER}@${DROPLET_IP}\" \"/opt/adventuretogether/deploy/update.sh --branch ${GIT_BRANCH}\""

  if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY-RUN] Would execute: ${SSH_CMD}"
  else
    ssh -i "${SSH_KEY_PATH}" \
        -o StrictHostKeyChecking=accept-new \
        "${SSH_USER}@${DROPLET_IP}" \
        "/opt/adventuretogether/deploy/update.sh --branch ${GIT_BRANCH}"
  fi

elif [ "${UPDATE_METHOD}" = "ansible" ]; then
  echo "Executing Ansible update playbook..."
  ANSIBLE_CMD="ansible-playbook -i \"${ANSIBLE_DIR}/inventory.ini\" \"${ANSIBLE_DIR}/update.yml\" -e \"git_branch=${GIT_BRANCH}\""

  if [ "${DRY_RUN}" = "true" ]; then
    echo "[DRY-RUN] Would execute: ${ANSIBLE_CMD}"
  else
    if command -v ansible-playbook >/dev/null 2>&1; then
      ansible-playbook -i "${ANSIBLE_DIR}/inventory.ini" "${ANSIBLE_DIR}/update.yml" -e "git_branch=${GIT_BRANCH}"
    else
      echo "Error: 'ansible-playbook' CLI is not found on your local system." >&2
      echo "Use '--method ssh' or install Ansible on your workstation." >&2
      exit 1
    fi
  fi
else
  echo "Error: Unknown update method '${UPDATE_METHOD}'. Supported methods are 'ssh' and 'ansible'." >&2
  exit 1
fi

echo "========================================================================"
echo "Update sequence initiated successfully."
echo "Verify application health at: http://${DROPLET_IP}/api/health/"
echo "========================================================================"
