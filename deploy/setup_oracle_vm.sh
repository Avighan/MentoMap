#!/usr/bin/env bash
# One-shot MentoMap deployment for a fresh Oracle Cloud "Always Free" VM
# (Ubuntu 22.04/24.04, arm64 Ampere A1 or amd64 micro shape — both work).
#
# Run this ON THE VM, as the default user (ubuntu), after SSHing in:
#   curl -fsSL https://raw.githubusercontent.com/<owner>/<repo>/main/deploy/setup_oracle_vm.sh -o setup.sh
#   chmod +x setup.sh
#   ./setup.sh
#
# Or just scp/paste this file onto the VM and run it directly. Safe to
# re-run — each step is idempotent (installs are skip-if-present, config
# files are overwritten with the same content, services are restarted).
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Avighan/MentoMap.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
APP_DIR="${APP_DIR:-$HOME/MentoMap}"
DOMAIN_OR_IP="${DOMAIN_OR_IP:-}"   # optional: your domain, for nginx server_name

echo "==> [1/8] Installing system packages"
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip nginx git curl

if ! command -v node >/dev/null 2>&1; then
  echo "==> Installing Node.js 20.x"
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi

echo "==> [2/8] Opening the VM's local firewall for HTTP (port 80)"
# Oracle's Ubuntu images ship with iptables rules that only allow port 22
# inbound by default — separate from (and in addition to) the VCN Security
# List you configure in the OCI web console. Both need to allow port 80.
if command -v iptables >/dev/null 2>&1; then
  sudo iptables -C INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null || \
    sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
  sudo netfilter-persistent save 2>/dev/null || \
    (sudo apt-get install -y iptables-persistent && sudo netfilter-persistent save)
fi

echo "==> [3/8] Fetching MentoMap ($REPO_BRANCH) into $APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" fetch origin "$REPO_BRANCH"
  git -C "$APP_DIR" checkout "$REPO_BRANCH"
  git -C "$APP_DIR" pull origin "$REPO_BRANCH"
else
  git clone --branch "$REPO_BRANCH" "$REPO_URL" "$APP_DIR"
fi

echo "==> [4/8] Backend: venv + dependencies"
cd "$APP_DIR/backend"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

echo "==> [5/8] Writing backend/.env (generates secrets on first run only)"
ENV_FILE="$APP_DIR/backend/.env.deploy"
if [ ! -f "$ENV_FILE" ]; then
  SECRET_KEY_VAL="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  JWT_SECRET_VAL="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  cat > "$ENV_FILE" <<EOF
SECRET_KEY=$SECRET_KEY_VAL
JWT_SECRET_KEY=$JWT_SECRET_VAL
FLASK_ENV=production
EOF
  echo "    Generated new secrets in $ENV_FILE (kept across re-runs)."
else
  echo "    Reusing existing secrets in $ENV_FILE."
fi

echo "==> [6/8] systemd service for the backend (gunicorn, single worker)"
sudo tee /etc/systemd/system/mentomap-backend.service > /dev/null <<EOF
[Unit]
Description=MentoMap Flask backend
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR/backend
EnvironmentFile=$ENV_FILE
ExecStart=$APP_DIR/backend/venv/bin/gunicorn --workers 1 --timeout 60 --bind 127.0.0.1:5001 app:app
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
# Single worker is deliberate: app.py holds significant per-process
# in-memory state (the games bundle cache, the run cache) that isn't
# shared across workers — this matches how it already runs locally.

sudo systemctl daemon-reload
sudo systemctl enable mentomap-backend
sudo systemctl restart mentomap-backend

echo "==> [7/8] Frontend: build static files"
cd "$APP_DIR/frontend-react"
npm ci
npm run build   # outputs to frontend-react/dist

echo "==> [8/8] nginx: serve the frontend build, reverse-proxy /api to gunicorn"
SERVER_NAME="${DOMAIN_OR_IP:-_}"
sudo tee /etc/nginx/sites-available/mentomap > /dev/null <<EOF
server {
    listen 80;
    server_name $SERVER_NAME;

    root $APP_DIR/frontend-react/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }

    location /health {
        proxy_pass http://127.0.0.1:5001;
    }

    # React Router: any non-file, non-/api path falls back to index.html
    location / {
        try_files \$uri /index.html;
    }
}
EOF
sudo ln -sf /etc/nginx/sites-available/mentomap /etc/nginx/sites-enabled/mentomap
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl enable nginx

PUBLIC_IP="$(curl -s -4 ifconfig.me || echo '<your-vm-public-ip>')"
echo ""
echo "================================================================"
echo " Done. Backend status:"
sudo systemctl --no-pager status mentomap-backend | head -5
echo ""
echo " Visit:  http://$PUBLIC_IP/"
echo " Health: http://$PUBLIC_IP/health"
echo ""
echo " Remember: the OCI web console's VCN Security List must ALSO allow"
echo " ingress on port 80 (0.0.0.0/0, TCP, port 80) — this script only"
echo " opened the VM's own firewall, not OCI's network-level one."
echo "================================================================"
