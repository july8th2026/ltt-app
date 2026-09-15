#!/bin/bash
# Install the OVH gwnat helper and freeze the currently proven mappings.
set -euo pipefail

SOURCE_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
MAP=/etc/wireguard/anh-xa-ip.txt
PROTECTED=/etc/ltt-vps/protected-gwnat.conf

[[ -s $MAP ]] || { echo 'mapping inventory is unavailable' >&2; exit 2; }
install -d -m 700 /etc/ltt-vps
if [[ ! -e $PROTECTED ]]; then
    install -m 600 "$MAP" "$PROTECTED"
fi
install -m 755 "$SOURCE_DIR/ltt-gwnat.sh" /usr/local/sbin/ltt-gwnat
/usr/local/sbin/ltt-gwnat health
echo 'installed ltt-gwnat; protected baseline preserved'
