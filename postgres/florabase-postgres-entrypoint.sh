#!/bin/sh
set -eu
# Florabase PostgreSQL entrypoint (ADR 0009):
# 1. Always refuse root before touching disk (exit 64, no backoff).
# 2. Validate data-directory layout, owners, modes, installation marker and cluster identity
#    before PostgreSQL initializes or starts.
# 3. Accept FLORABASE_DB_PASSWORD as the single stack password variable, then exec upstream.
florabase-postgres-refuse-root || exit 64

if [ "$#" -gt 0 ] && [ "$1" != "postgres" ] && [ "${1#-}" = "$1" ]; then
    exec docker-entrypoint.sh "$@"
fi
for arg in "$@"; do
    case "$arg" in
        '-?'|--help|--describe-config|-V|--version) exec docker-entrypoint.sh "$@" ;;
    esac
done

refuse() {
    echo "florabase-db: REFUSED: $*" >&2
    backoff="${FLORABASE_REFUSAL_BACKOFF_SECONDS:-3}"
    if [ "$backoff" != "0" ]; then
        sleep "$backoff"
    fi
    exit 1
}

if [ -z "${POSTGRES_PASSWORD:-}" ] && [ -n "${FLORABASE_DB_PASSWORD:-}" ]; then
    export POSTGRES_PASSWORD="$FLORABASE_DB_PASSWORD"
fi
if [ "${FLORABASE_DB_PASSWORD:-}" = "change-me" ] || [ "${POSTGRES_PASSWORD:-}" = "change-me" ]; then
    refuse "FLORABASE_DB_PASSWORD is still the placeholder 'change-me'; set a strong password (see docs/installation.md)"
fi

root="${FLORABASE_PG_ROOT:-/var/lib/postgresql}"
marker="$root/state/installation.env"
pending="$root/postgres/installation.pending"
export PGDATA="$root/postgres/$PG_MAJOR/docker"

[ -d "$root" ] && [ -x "$root" ] || refuse \
    "data folder $root is not searchable by uid 70; run the folder setup commands in docs/installation.md"

check_dir() {
    path="$1"
    want_owner="$2"
    want_mode="$3"
    [ ! -L "$path" ] && [ -d "$path" ] || refuse \
        "missing required folder $path; run the folder setup commands in docs/installation.md"
    owner="$(stat -c '%u:%g' "$path")"
    mode="$(stat -c '%a' "$path")"
    [ "$owner" = "$want_owner" ] || refuse \
        "$path has owner $owner, expected $want_owner; run the folder setup commands in docs/installation.md"
    [ "$mode" = "$want_mode" ] || refuse \
        "$path has mode $mode, expected $want_mode; run the folder setup commands in docs/installation.md"
}

check_dir "$root/postgres" "70:70" "700"
check_dir "$root/media" "10001:10001" "700"
check_dir "$root/state" "10001:10001" "755"

if [ -e "$marker" ] || [ -L "$marker" ]; then
    [ ! -L "$marker" ] && [ -f "$marker" ] && [ -r "$marker" ] || refuse \
        "the installation marker is not readable"
    major="$(sed -n 's/^FLORABASE_PG_MAJOR=\([0-9][0-9]*\)$/\1/p' "$marker")"
    system="$(sed -n 's/^FLORABASE_PG_SYSTEM_ID=\([0-9][0-9]*\)$/\1/p' "$marker")"
    [ -n "$major" ] && [ -n "$system" ] || refuse "the installation marker is malformed"
    [ "$major" = "$PG_MAJOR" ] || refuse \
        "the installation uses PostgreSQL $major, this image $PG_MAJOR"
    cluster="$root/postgres/$major/docker"
    [ -s "$cluster/PG_VERSION" ] || refuse \
        "the installation marker exists but its database folder is missing or empty"
    found="$(pg_controldata "$cluster" 2>/dev/null | sed -n 's/^Database system identifier: *//p' || true)"
    [ "$found" = "$system" ] || refuse \
        "the database folder belongs to another PostgreSQL cluster"
    rm -f "$pending"
else
    [ -r "$root" ] || refuse \
        "data folder $root is not readable by uid 70; run the folder setup commands in docs/installation.md"
    retry=
    [ ! -e "$pending" ] || retry=1
    for entry in "$root"/* "$root"/.[!.]* "$root"/..?*; do
        [ -e "$entry" ] || [ -L "$entry" ] || continue
        case "$entry" in
            "$root/postgres")
                [ -n "$retry" ] || [ -z "$(ls -A "$entry")" ] || refuse \
                    "$entry is not empty and there is no installation marker; use an empty data folder"
                ;;
            "$root/state")
                for item in "$entry"/* "$entry"/.[!.]* "$entry"/..?*; do
                    [ -e "$item" ] || [ -L "$item" ] || continue
                    if [ -n "$retry" ] && [ "$item" = "$entry/installation.pending" ]; then
                        continue
                    fi
                    refuse \
                        "$entry is not empty and there is no installation marker; use an empty data folder"
                done
                ;;
            "$root/media")
                # media/ is mode 0700 owned by 10001:10001; backend verifies it is empty on first install.
                ;;
            *)
                refuse "$entry exists and there is no installation marker; use an empty data folder"
                ;;
        esac
    done
    [ -e "$pending" ] || touch "$pending"
fi

exec docker-entrypoint.sh "$@"
