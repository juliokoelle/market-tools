#!/usr/bin/env bash
# =============================================================================
# Julio's n8n VPS setup — run as root on fresh Ubuntu 24.04 (Hetzner CX11)
# =============================================================================
set -euo pipefail

echo "=== [1/5] System packages ==="
apt-get update -qq
apt-get install -y -qq \
  curl git python3 python3-pip python3-venv \
  nginx certbot python3-certbot-nginx \
  ca-certificates gnupg

echo "=== [2/5] Docker ==="
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | tee /etc/apt/sources.list.d/docker.list
apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl enable docker
systemctl start docker

echo "=== [3/5] Automation repo (for Gmail briefing script) ==="
mkdir -p /app
cd /app
git clone https://github.com/juliokoelle/market-tools.git automation
cd automation
python3 -m venv venv
venv/bin/pip install --quiet -r requirements.txt
echo "Repo cloned to /app/automation"

echo "=== [4/5] nginx placeholder ==="
rm -f /etc/nginx/sites-enabled/default
cat > /etc/nginx/sites-available/n8n <<'NGINX'
server {
    listen 80;
    server_name _;
    location / {
        proxy_pass http://localhost:5678;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
NGINX
ln -sf /etc/nginx/sites-available/n8n /etc/nginx/sites-enabled/n8n
nginx -t && systemctl reload nginx

echo "=== [5/5] n8n env file ==="
mkdir -p /opt/n8n
if [ ! -f /opt/n8n/.env ]; then
  cp /app/automation/infra/.env.example /opt/n8n/.env
  echo ""
  echo ">>> ACTION REQUIRED: edit /opt/n8n/.env with your credentials <<<"
  echo ""
fi

echo ""
echo "============================================================"
echo "Setup done. Next steps:"
echo ""
echo "1. Edit  /opt/n8n/.env   (fill in all credentials)"
echo "2. Point your domain DNS A-record to this server's IP"
echo "3. Run:  certbot --nginx -d <your-domain>  (for HTTPS)"
echo "4. Start n8n:"
echo "   cd /app/automation && docker compose -f infra/docker-compose.yml --env-file /opt/n8n/.env up -d"
echo "5. Open https://<your-domain>  — import workflows from infra/workflows/"
echo "6. Set Telegram webhook:"
echo "   curl 'https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://<your-domain>/webhook/telegram-bot'"
echo "7. Find your TELEGRAM_CHAT_ID:"
echo "   Send a message to the bot, check the n8n execution log for message.chat.id"
echo "8. Disable Mac LaunchAgents (see infra/MIGRATION.md)"
echo "============================================================"
