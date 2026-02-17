#!/bin/bash
set -euo pipefail

# STRATYON Backend - EC2 Instance Setup Script
# Run this once on a fresh Ubuntu 24.04 EC2 instance
#
# Usage: sudo bash scripts/setup-ec2.sh
#
# Prerequisites:
#   - EC2 t3.small (or larger) with Ubuntu 24.04 AMI
#   - Security group: ports 22, 80, 443 inbound
#   - Elastic IP attached
#   - IAM role with SSM Parameter Store read access and S3 write access

echo "=== STRATYON EC2 Setup ==="

# 1. System updates
echo "[1/7] Updating system packages..."
apt-get update && apt-get upgrade -y

# 2. Install Docker
echo "[2/7] Installing Docker..."
apt-get install -y docker.io docker-compose-v2
systemctl enable docker
systemctl start docker
usermod -aG docker ubuntu

# 3. Install AWS CLI
echo "[3/7] Installing AWS CLI..."
apt-get install -y awscli

# 4. Install Caddy
echo "[4/7] Installing Caddy..."
apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt-get update
apt-get install -y caddy

# 5. Setup swap file (safety net for t3.small 2GB RAM)
echo "[5/7] Setting up 1GB swap..."
if [ ! -f /swapfile ]; then
    fallocate -l 1G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    # Reduce swappiness - only use swap under memory pressure
    echo 'vm.swappiness=10' >> /etc/sysctl.conf
    sysctl -p
fi

# 6. Create application directory
echo "[6/7] Setting up application directory..."
mkdir -p /opt/stratyon
chown ubuntu:ubuntu /opt/stratyon

# 7. Configure Docker log rotation
echo "[7/7] Configuring Docker log rotation..."
cat > /etc/docker/daemon.json <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF
systemctl restart docker

# Setup daily database backup cron (runs at 3 AM UTC)
echo "Setting up daily database backup cron..."
BACKUP_CRON='0 3 * * * /opt/stratyon/scripts/backup-db.sh >> /var/log/stratyon-backup.log 2>&1'
(crontab -u ubuntu -l 2>/dev/null; echo "$BACKUP_CRON") | crontab -u ubuntu -

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Clone your repo:    cd /opt/stratyon && git clone <your-repo-url> ."
echo "  2. Pull secrets:       bash scripts/pull-secrets.sh"
echo "  3. Start services:     docker compose -f docker-compose.prod.yml up -d"
echo "  4. Configure Caddy:    Edit /etc/caddy/Caddyfile with your domain"
echo "  5. Create S3 bucket:   aws s3 mb s3://stratyon-backups"
echo ""
echo "NOTE: Log out and back in for docker group to take effect."
