#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."

# Resolve the canonical lock file identically to workflow_resources.lock_root()
# (uses FLORABASE_LOCK_DIR or the account's passwd home rather than $HOME).
LOCK_FILE="$(python3 -c '
import sys
from pathlib import Path
sys.path.insert(0, str(Path("scripts").resolve()))
from workflow_resources import lock_root
print(lock_root() / "florabase-perf.lock")
')"

if [ "${FLORABASE_PERF_LOCK_FD+set}" = "set" ]; then
  # Synchronous parent-held lock inheritance (from measure.py pass_fds only):
  # validate descriptor format, device/inode against LOCK_FILE, regular-file mode,
  # and active non-blocking flock without calling LOCK_UN or touching parent lock state.
  python3 - "$LOCK_FILE" "$FLORABASE_PERF_LOCK_FD" <<'PY'
import errno
import fcntl
import os
import re
import stat
import sys

lock_file, raw_fd = sys.argv[1], sys.argv[2]
if not re.fullmatch(r"[0-9]+", raw_fd) or int(raw_fd) < 3:
    print(f"Refusing invalid FLORABASE_PERF_LOCK_FD={raw_fd!r}", file=sys.stderr)
    sys.exit(1)
fd = int(raw_fd)
try:
    st_fd = os.fstat(fd)
except OSError as error:
    print(f"Refusing unusable FLORABASE_PERF_LOCK_FD={fd}: {error}", file=sys.stderr)
    sys.exit(1)
if not stat.S_ISREG(st_fd.st_mode):
    print(f"Refusing non-regular FLORABASE_PERF_LOCK_FD={fd}", file=sys.stderr)
    sys.exit(1)
try:
    st_lock = os.stat(lock_file)
except OSError as error:
    print(f"Canonical lock file missing ({lock_file}): {error}", file=sys.stderr)
    sys.exit(1)
if (st_fd.st_dev, st_fd.st_ino) != (st_lock.st_dev, st_lock.st_ino):
    print(
        f"Refusing mismatched FLORABASE_PERF_LOCK_FD={fd} (does not match {lock_file})",
        file=sys.stderr,
    )
    sys.exit(1)
try:
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except OSError as error:
    if error.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
        print(
            f"Refusing unlocked or contended FLORABASE_PERF_LOCK_FD={fd} for {lock_file}",
            file=sys.stderr,
        )
    else:
        print(f"Lock verification failed on fd {fd}: {error}", file=sys.stderr)
    sys.exit(1)
PY
  # Close the inherited fd in the child shell before exec so docker compose
  # and any child processes it spawns never retain parent lock descriptors;
  # the parent FileLock keeps the open file description locked.
  eval "exec ${FLORABASE_PERF_LOCK_FD}<&-"
else
  mkdir -p "$(dirname "$LOCK_FILE")"
  # Open non-truncating (>>) so refused acquisition never clobbers active holder diagnostics.
  exec 9>>"$LOCK_FILE"
  if ! flock -n 9; then
    echo "florabase-perf lifecycle lock is held by another invocation; wait and retry" >&2
    exit 1
  fi
fi

# Never load the operator's .env; fixed project and disposable credentials.
export POSTGRES_DB=florabase_perf POSTGRES_USER=florabase_perf
export POSTGRES_PASSWORD=disposable-perf-password
export FLORABASE_DATABASE_URL=postgresql+psycopg://florabase_perf:disposable-perf-password@db:5432/florabase_perf
export FLORABASE_CANONICAL_ORIGIN=http://localhost:18080
exec docker compose --env-file /dev/null --project-name florabase-perf \
  --file compose.yaml --file compose.perf.yaml "$@"
