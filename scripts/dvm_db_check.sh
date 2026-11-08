#!/bin/bash
# DVM database size check — runs nightly via root crontab.
#
# Replaces the old unconditional PM2 cron restart ("0 4 * * *") which caused
# the Oct/Nov 2026 outages: the Python DVMs ignore SIGTERM, and the daily
# PM2 kill/restart race occasionally left apps stuck in 'errored' state
# (e.g. discovery id=8 offline from Oct 27 to Nov 8, 2026).
#
# Instead: only restart a DVM if its LMDB database exceeded its size limit.
# The restart is what triggers the wipe+resync (init_db with wipe=True,
# limit=2048MB, enabled 2026-11-08). LMDB files never shrink after
# delete_events, so a restart is the only way to reclaim space.
#
# Install on the VPS at /root/dvm/dvm_db_check.sh with crontab entry:
#   0 4 * * * /root/dvm/dvm_db_check.sh >> /var/log/dvm_db_check.log 2>&1

set -u
export PATH=/root/.nvm/versions/node/v20.17.0/bin:$PATH

LIMIT_MB=2048

check() {
    local app="$1" db="$2"
    if [ ! -f "$db/data.mdb" ]; then
        echo "$(date -Is) $app: $db missing, skipping"
        return 0
    fi
    local size_mb
    size_mb=$(( $(stat -c%s "$db/data.mdb") / 1024 / 1024 ))
    if [ "$size_mb" -gt "$LIMIT_MB" ]; then
        echo "$(date -Is) $app: $db is ${size_mb}MB > ${LIMIT_MB}MB — restarting (wipe on startup)"
        pm2 restart "$app"
    else
        echo "$(date -Is) $app: $db ${size_mb}MB <= ${LIMIT_MB}MB — no restart"
    fi
}

check discovery                      /root/dvm/db/nostr_recent_notes.db
check discovery_on_this_day_and_olas /root/dvm/db/nostr_on_this_day.db
check discovery_on_this_day_and_olas /root/dvm/db/nostr_olas.db
