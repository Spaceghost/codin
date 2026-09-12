#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
WORK="$ROOT/.c99-work"
TOOLS="$ROOT/tools/c99-experimental"

rm -rf "$WORK"
mkdir -p "$WORK"
cp -R "$ROOT/src" "$WORK/src"

patch --batch --forward -d "$WORK" -p1 < \
    "$TOOLS/patches/0001-preserve-positional-compound-values.patch"

for pass in augment_c99 augment_slice_string augment_multi_return augment_defer augment_union; do
    python3 "$TOOLS/$pass.py" "$WORK/src/c99.c"
done

make -C "$ROOT" clean >/dev/null 2>&1 || true
make -C "$ROOT" SRCDIR="$WORK/src"
printf '%s\n' "codin experimental strict C99 backend built"
