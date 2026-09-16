#!/usr/bin/env bash
# Chay SearXNG rieng o foreground (giu distro WSL song). ASCII only.
#   wsl.exe -d Ubuntu -u root -- bash /mnt/d/<cay>/tools/lttcode_searxng/chay.sh
# uWSGI tu ha quyen xuong user searxng (uwsgi.ini: uid/gid).
set -euo pipefail
exec /usr/bin/uwsgi --ini /etc/searxng/uwsgi.ini
