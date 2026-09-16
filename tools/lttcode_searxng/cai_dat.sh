#!/usr/bin/env bash
# Cai / cap nhat SearXNG rieng cho tim kiem LTTCODE (P06). ASCII only.
#
#   wsl.exe -d Ubuntu -u root -- bash /mnt/d/<cay>/tools/lttcode_searxng/cai_dat.sh
#
# Idempotent: chay lai = cap nhat ma SearXNG (git pull) + pip, GIU secret_key.
# Chi nghe 127.0.0.1:8888 trong WSL2 (localhostForwarding) - khong mo ra LAN/Internet.
# Theo tai lieu chinh thuc: docs.searxng.org/admin/installation-searxng.html (step by step,
# uWSGI). Khong bat systemd va khong sua /etc/wsl.conf: tools/lttcode_searxng/chay.sh
# chay uWSGI o foreground, Scheduled Task giu no song (tools/lttcode_searxng/dang_ky_task.ps1).
set -euo pipefail

PORT="${SEARXNG_PORT:-8888}"
HOME_DIR=/usr/local/searxng
SRC="$HOME_DIR/searxng-src"
VENV="$HOME_DIR/searx-pyenv"
CONF=/etc/searxng
REPO=https://github.com/searxng/searxng

as_searxng() { runuser -u searxng -- "$@"; }

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3-dev python3-babel python3-venv python-is-python3 \
  uwsgi uwsgi-plugin-python3 git build-essential libxslt-dev zlib1g-dev libffi-dev \
  libssl-dev ca-certificates curl openssl >/dev/null

id searxng >/dev/null 2>&1 || useradd --shell /bin/bash --system --home-dir "$HOME_DIR" \
  --comment "LTT private SearXNG" searxng
mkdir -p "$HOME_DIR"
chown -R searxng:searxng "$HOME_DIR"

if [ -d "$SRC/.git" ]; then
  as_searxng git -C "$SRC" pull -q --ff-only
else
  as_searxng git clone -q --depth 1 "$REPO" "$SRC"
fi
[ -x "$VENV/bin/python" ] || as_searxng python3 -m venv "$VENV"
# Same pre-install list as upstream utils/searxng.sh (searxng.install.pyenv): the
# editable install imports searx while building metadata, so its deps come first.
as_searxng "$VENV/bin/pip" install -q -U pip setuptools wheel pyyaml msgspec typing-extensions pybind11
as_searxng bash -c "cd '$SRC' && '$VENV/bin/pip' install -q --use-pep517 --no-build-isolation -e ."

mkdir -p "$CONF"
if [ ! -f "$CONF/settings.yml" ]; then
  SECRET="$(openssl rand -hex 32)"
  cat > "$CONF/settings.yml" <<EOF
# LTT private SearXNG - backend cua POST /lttcode/search (LTTSTUDIOSAPP apps/lttcode).
use_default_settings:
  engines:
    keep_only:
      - brave
      - duckduckgo
      - wikipedia
      - github
      - stackoverflow
      - askubuntu
      - superuser
      - mdn
      - pypi
      - docker hub
      - arch linux wiki
      - npm
      - crates.io

general:
  instance_name: "LTT private search"
  enable_metrics: false

server:
  port: ${PORT}
  bind_address: "127.0.0.1"
  secret_key: "${SECRET}"
  limiter: false
  public_instance: false
  image_proxy: false

search:
  safe_search: 0
  formats:
    - html
    - json

outgoing:
  request_timeout: 4.0
  max_request_timeout: 10.0

valkey:
  url: false

engines:
  - name: npm
    disabled: false
  - name: crates.io
    disabled: false
EOF
fi

cat > "$CONF/uwsgi.ini" <<EOF
[uwsgi]
plugin = python3
uid = searxng
gid = searxng
env = LANG=C.UTF-8
env = LANGUAGE=C.UTF-8
env = LC_ALL=C.UTF-8
env = SEARXNG_SETTINGS_PATH=${CONF}/settings.yml
chdir = ${SRC}/searx
pythonpath = ${SRC}
virtualenv = ${VENV}
module = searx.webapp
master = true
lazy-apps = true
enable-threads = true
workers = 2
threads = 4
http-socket = 127.0.0.1:${PORT}
buffer-size = 8192
disable-logging = true
die-on-term = true
EOF

chown root:searxng "$CONF/settings.yml" "$CONF/uwsgi.ini"
chmod 640 "$CONF/settings.yml" "$CONF/uwsgi.ini"

# Ban chay nam TRONG distro: Scheduled Task tro vao day, khong phu thuoc cay ma nguon.
install -m 755 /dev/stdin "$HOME_DIR/chay.sh" <<'EOF'
#!/usr/bin/env bash
# LTT private SearXNG, foreground (keeps the WSL distro alive). Started by the
# Windows Scheduled Task "LTT SearXNG (LTTCODE search)".
set -euo pipefail
exec /usr/bin/uwsgi --ini /etc/searxng/uwsgi.ini
EOF
echo "SEARXNG_INSTALL_OK $(as_searxng git -C "$SRC" log -1 --format='%h %cs')"
