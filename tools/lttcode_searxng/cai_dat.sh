#!/usr/bin/env bash
# Cai / cap nhat SearXNG rieng cho tim kiem LTTCODE (P06). ASCII only.
#
#   wsl.exe -d Ubuntu -u root -- bash /mnt/d/<cay>/tools/lttcode_searxng/cai_dat.sh
#
# Idempotent: chay lai = cap nhat ma SearXNG (git pull) + pip, GIU secret_key.
# settings.yml duoc DUNG LAI tu settings.template.yml (cung thu muc) moi lan chay; ban cu
# (neu khac) duoc giu o settings.yml.bak-<UTC time>. Chi ap cau hinh, bo qua apt/git/pip:
#   wsl.exe -d Ubuntu -u root -- env CHI_CAU_HINH=1 bash /mnt/d/<cay>/tools/lttcode_searxng/cai_dat.sh
# roi khoi dong lai: Stop-ScheduledTask "LTT SearXNG (LTTCODE search)"; Stop-ScheduledTask chi giet
# wsl.exe, uWSGI trong distro VAN SONG (do 17/09) -> wsl.exe -d Ubuntu -u root -- pkill -TERM -x uwsgi,
# doi het tien trinh uwsgi, roi Start-ScheduledTask. Khong giet thi task moi thoat ngay (cong 8888 dang bi giu).
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
TEMPLATE="$(cd "$(dirname "$0")" && pwd)/settings.template.yml"
[ -f "$TEMPLATE" ] || { echo "missing $TEMPLATE" >&2; exit 1; }

as_searxng() { runuser -u searxng -- "$@"; }

if [ "${CHI_CAU_HINH:-0}" != "1" ]; then
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

fi

mkdir -p "$CONF"
SECRET=""
if [ -f "$CONF/settings.yml" ]; then
  SECRET="$( { grep -oE '^[[:space:]]*secret_key:[[:space:]]*"?[0-9a-fA-F]{32,}' "$CONF/settings.yml" || true; } | grep -oE '[0-9a-fA-F]{32,}$' | head -n 1 || true)"
fi
[ -n "$SECRET" ] || SECRET="$(openssl rand -hex 32)"
NEW="$(mktemp)"
sed -e "s/__PORT__/${PORT}/" -e "s/__SECRET_KEY__/${SECRET}/" "$TEMPLATE" > "$NEW"
if [ -f "$CONF/settings.yml" ] && ! cmp -s "$NEW" "$CONF/settings.yml"; then
  cp -p "$CONF/settings.yml" "$CONF/settings.yml.bak-$(date -u +%Y%m%dT%H%M%SZ)"
fi
install -m 640 "$NEW" "$CONF/settings.yml"
rm -f "$NEW"
unset SECRET

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
# cat + chmod, not "install /dev/stdin <<EOF": that exits 1 (ENOENT) in this WSL Ubuntu (seen 17/09).
cat > "$HOME_DIR/chay.sh" <<'EOF'
#!/usr/bin/env bash
# LTT private SearXNG, foreground (keeps the WSL distro alive). Started by the
# Windows Scheduled Task "LTT SearXNG (LTTCODE search)".
set -euo pipefail
exec /usr/bin/uwsgi --ini /etc/searxng/uwsgi.ini
EOF
chmod 755 "$HOME_DIR/chay.sh"
if [ "${CHI_CAU_HINH:-0}" = "1" ]; then echo "SEARXNG_CONFIG_OK"; else
  echo "SEARXNG_INSTALL_OK $(as_searxng git -C "$SRC" log -1 --format='%h %cs')"
fi
