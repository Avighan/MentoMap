# Deploying MentoMap to an Oracle Cloud "Always Free" VM

Two parts: things only you can do (account + VM, in your browser), and
one script that does everything else.

## Part A — Create the VM (you do this)

1. **Sign up**: go to https://signup.oraclecloud.com, create an account.
   Requires phone verification and a card for identity checks (you are
   not charged for Always Free resources).
2. **Create a VCN** (Virtual Cloud Network): in the console, use
   *Networking → Virtual Cloud Networks → Start VCN Wizard* → "Create VCN
   with Internet Connectivity" and accept the defaults. This gives you a
   public subnet + internet gateway automatically.
3. **Open port 80 in the Security List**: *Networking → Virtual Cloud
   Networks → (your VCN) → Security Lists → Default Security List → Add
   Ingress Rules*:
   - Source CIDR: `0.0.0.0/0`, IP Protocol: TCP, Destination Port: `80`
   - (Optional, for HTTPS later): same but port `443`
4. **Create the instance**: *Compute → Instances → Create Instance*:
   - Image: **Ubuntu 22.04** (or 24.04)
   - Shape: click "Change shape" → **Ampere (Arm)**, `VM.Standard.A1.Flex`,
     4 OCPU / 24GB (all still free tier) — if unavailable in your region,
     fall back to the AMD `VM.Standard.E2.1.Micro` shape instead.
   - Networking: use the VCN from step 2, check "Assign a public IPv4
     address".
   - SSH keys: let Oracle generate a key pair and **download the private
     key** (or paste your own public key if you already have one).
5. **Note the public IP** shown on the instance's detail page once it's
   running.
6. **SSH in**:
   ```bash
   chmod 400 ~/Downloads/ssh-key-....key
   ssh -i ~/Downloads/ssh-key-....key ubuntu@<the-public-ip>
   ```

## Part B — Run the setup script (on the VM)

If `Avighan/MentoMap` is **public**, just run:

```bash
curl -fsSL https://raw.githubusercontent.com/Avighan/MentoMap/main/deploy/setup_oracle_vm.sh -o setup.sh
chmod +x setup.sh
./setup.sh
```

If the repo is **private**, either:
- generate a GitHub [personal access token](https://github.com/settings/tokens)
  (repo read scope) and run:
  ```bash
  export REPO_URL="https://<token>@github.com/Avighan/MentoMap.git"
  ./setup.sh
  ```
- or copy `deploy/setup_oracle_vm.sh` to the VM manually (`scp` it over)
  and run it there — it will prompt for nothing, just needs `REPO_URL`
  set the same way if cloning fails.

The script installs Python/Node/nginx, builds the backend venv and the
frontend, sets up a systemd service (`mentomap-backend`) running the
Flask app under gunicorn, and configures nginx to serve the built
frontend and reverse-proxy `/api/*` to the backend. It's safe to re-run
(e.g. after `git pull`ing new changes) — it'll rebuild and restart in
place.

When it finishes it prints the URL to open:

```
Visit:  http://<your-vm-public-ip>/
Health: http://<your-vm-public-ip>/health
```

## Updating after future code changes

```bash
ssh -i your-key.key ubuntu@<ip>
cd ~/MentoMap && git pull
./deploy/setup_oracle_vm.sh
```

## Data persistence

Unlike most free PaaS tiers, this is a real VM with a real disk —
`backend/data/` (users, runs, wallets, leaderboards — all JSON files)
persists across restarts and redeploys as long as you don't `rm -rf` it.
There's no separate database to configure.

## Troubleshooting

- **Nothing loads at all**: almost always the OCI Security List (Part A,
  step 3) — the VM's own firewall is opened by the script, but the
  network-level rule in the OCI console is separate and easy to miss.
- **502 from nginx**: the backend service isn't up —
  `sudo systemctl status mentomap-backend` and
  `sudo journalctl -u mentomap-backend -n 50` to see why.
- **Frontend loads but API calls fail**: check the browser console/network
  tab for the actual URL being called — it should be a relative `/api/...`
  path on the same origin, handled by nginx's `location /api/` block.
