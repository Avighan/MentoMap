#!/usr/bin/env bash
# Local rotating backup of backend/data — the JSON-file storage layer that
# holds every user account, game run, and wallet/notification record.
#
# This protects against the everyday failure modes (a bad app bug corrupts
# a JSON file, an accidental `rm`, a botched manual edit) by keeping the
# last N nightly snapshots on the VM's own disk. It does NOT protect
# against losing the VM/disk itself — for that, copy the tarballs in
# $BACKUP_DIR off the instance periodically (e.g. `scp` them down, or push
# to OCI Object Storage) — see deploy/README.md.
#
# Installed as a systemd timer by setup_oracle_vm.sh; safe to also run by
# hand: ./deploy/backup_data.sh
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/MentoMap}"
DATA_DIR="$APP_DIR/backend/data"
BACKUP_DIR="${BACKUP_DIR:-$HOME/mentomap-backups}"
KEEP=20   # ~2-3 weeks of nightly snapshots before older ones are pruned

if [ ! -d "$DATA_DIR" ]; then
  echo "No $DATA_DIR yet — nothing to back up." >&2
  exit 0
fi

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
ARCHIVE="$BACKUP_DIR/data-$STAMP.tar.gz"

tar -czf "$ARCHIVE" -C "$APP_DIR/backend" data
echo "Backed up $DATA_DIR -> $ARCHIVE ($(du -h "$ARCHIVE" | cut -f1))"

# Prune down to the most recent $KEEP archives.
ls -1t "$BACKUP_DIR"/data-*.tar.gz 2>/dev/null | tail -n "+$((KEEP + 1))" | \
  while read -r old; do rm -f "$old"; echo "Pruned old backup: $old"; done
