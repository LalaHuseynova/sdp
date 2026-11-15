#!/bin/bash
# Tier-2 archive of one SQLite file (owner-approved 2026-11-15). Stops at the first failure.
set -euo pipefail
DIR="$1"; F=queries.sqlite; A=queries.sqlite.tar.gz
TMP="$2/$(basename "$DIR")"; mkdir -p "$TMP"
test -f "$DIR/$F" && test ! -e "$DIR/$A" && test ! -e "$DIR/$F-wal" && test ! -e "$DIR/$F-journal"
ORIG=$(shasum -a 256 "$DIR/$F" | cut -d' ' -f1); SIZE=$(stat -f %z "$DIR/$F")
tar -czf "$DIR/$A" -C "$DIR" "$F"
tar -tzf "$DIR/$A" | grep -qx "$F"                       # archive lists exactly the file
tar -xzf "$DIR/$A" -C "$TMP"                              # extraction succeeds
REST=$(shasum -a 256 "$TMP/$F" | cut -d' ' -f1)
test "$REST" = "$ORIG"                                     # restored == original, byte for byte
test "$(sqlite3 "file:$TMP/$F?mode=ro" 'PRAGMA integrity_check')" = ok
ASHA=$(shasum -a 256 "$DIR/$A" | cut -d' ' -f1); ASIZE=$(stat -f %z "$DIR/$A")
echo "$DIR|$SIZE|$ORIG|$ASIZE|$ASHA|$REST"
rm "$DIR/$F"; rm -r "$TMP"
