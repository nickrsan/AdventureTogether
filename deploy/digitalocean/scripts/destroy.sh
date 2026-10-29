#!/usr/bin/env bash
# ==============================================================================
# AdventureTogether - DigitalOcean Infrastructure Teardown Script
# ==============================================================================
# Destroys all provisioned DigitalOcean resources managed by Terraform/OpenTofu
# (Droplet VM, VPC Network, Edge Firewall, DNS records, and Project associations).
# Pre-existing user-specified Reserved IPv4 addresses are safely unassigned and preserved.
#
# Usage:
#   ./destroy.sh --token "<DO_API_TOKEN>" [options]
#
# Options:
#   --token, -t        DigitalOcean Personal Access Token (or set DIGITALOCEAN_TOKEN)
#   --auto-approve     Skip interactive confirmation prompt
#   --help, -h         Show this help message
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="${SCRIPT_DIR}/../terraform"

DO_TOKEN="${DIGITALOCEAN_TOKEN:-${DO_TOKEN:-}}"
AUTO_APPROVE="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --token|-t)
      DO_TOKEN="$2"
      shift 2
      ;;
    --auto-approve)
      AUTO_APPROVE="true"
      shift 1
      ;;
    --help|-h)
      echo "Usage: ./destroy.sh --token <DO_API_TOKEN> [--auto-approve]"
      exit 0
      ;;
    *)
      echo "Error: Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [ -z "${DO_TOKEN}" ]; then
  echo "Error: DigitalOcean API Token is required to destroy resources." >&2
  exit 1
fi

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

cd "${TF_DIR}"

echo "WARNING: This will destroy all AdventureTogether infrastructure on DigitalOcean."
if [ "${AUTO_APPROVE}" = "true" ]; then
  "${IAC_BIN}" destroy -auto-approve -var="do_token=${DO_TOKEN}"
else
  "${IAC_BIN}" destroy -var="do_token=${DO_TOKEN}"
fi

echo "Teardown complete."
