#!/bin/sh
# The receiver bounds this small database backup to its deployment deadline.
set -eu
umask 077
dir=/mnt/spektr/server/data/dedhed-core/backups
file="$dir/dedhed-$(date -u +%Y%m%dT%H%M%SZ)-pre-core-deploy.dump"
docker exec dedhed-core-db-1 pg_dump -U core -d core -Fc > "$file.part"
docker exec -i dedhed-core-db-1 pg_restore -l < "$file.part" > /dev/null
mv "$file.part" "$file"
printf 'backup %s\n' "$file"

