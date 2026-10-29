# ==============================================================================
# AdventureTogether - DigitalOcean Terraform Outputs
# ==============================================================================
# Summarizes all actionable connection strings, endpoints, and identifiers
# resulting from the provisioning process.
# ==============================================================================

output "droplet_id" {
  description = "DigitalOcean Droplet instance identifier."
  value       = digitalocean_droplet.app_server.id
}

output "droplet_ipv4" {
  description = "Direct public IPv4 address assigned to the Droplet."
  value       = digitalocean_droplet.app_server.ipv4_address
}

output "effective_public_ipv4" {
  description = "The effective public IPv4 address routed to the application (Reserved IP if configured, else Droplet IP)."
  value       = local.effective_public_ipv4
}

output "droplet_ipv6" {
  description = "Public IPv6 address assigned to the Droplet."
  value       = digitalocean_droplet.app_server.ipv6_address
}

output "application_url" {
  description = "Public URL to access the AdventureTogether Vue 3 frontend web interface."
  value = (
    var.domain_name != "" ?
    "https://${var.domain_name}" :
    "http://${local.effective_public_ipv4}"
  )
}

output "api_health_check_url" {
  description = "Public URL for automated synthetic monitoring and health checks."
  value = (
    var.domain_name != "" ?
    "https://${var.domain_name}/api/health/" :
    "http://${local.effective_public_ipv4}/api/health/"
  )
}

output "ssh_command" {
  description = "Terminal command to securely connect to the provisioned Droplet."
  value       = "ssh deploy@${local.effective_public_ipv4}"
}

output "ssh_root_command" {
  description = "Terminal command for direct root access."
  value       = "ssh root@${local.effective_public_ipv4}"
}

output "vpc_id" {
  description = "DigitalOcean VPC Network identifier."
  value       = digitalocean_vpc.app_vpc.id
}

output "project_id" {
  description = "DigitalOcean Project identifier."
  value       = digitalocean_project.app_project.id
}

output "auto_generated_ssh_private_key" {
  description = "Auto-generated SSH private key (if no public key or registered key was supplied)."
  value       = var.ssh_key_name == "" && var.ssh_public_key == "" ? tls_private_key.auto_generated[0].private_key_pem : "N/A (Pre-existing or user-provided key used)"
  sensitive   = true
}

output "ssh_private_key_path" {
  description = "Filesystem path to the local SSH private key."
  value       = var.ssh_key_name == "" && var.ssh_public_key == "" ? "${path.module}/id_ed25519" : "N/A (Pre-existing or user-provided key used)"
}

output "ansible_inventory_content" {
  description = "Generated Ansible inventory configuration targeting the provisioned Droplet."
  value       = "[app_servers]\ndroplet ansible_host=${local.effective_public_ipv4} ansible_user=deploy ansible_ssh_private_key_file=${var.ssh_key_name == "" && var.ssh_public_key == "" ? "${path.module}/id_ed25519" : "~/.ssh/id_rsa"}\n"
}

output "ansible_deploy_command" {
  description = "Exact Ansible command to deploy or configure the application on the Droplet."
  value       = "ansible-playbook -i deploy/ansible/inventory.ini deploy/ansible/playbook.yml"
}

output "postgis_backup_path" {
  description = "Filesystem path on the Droplet where daily automated PostGIS backups are stored."
  value       = "/var/backups/adventuretogether"
}
