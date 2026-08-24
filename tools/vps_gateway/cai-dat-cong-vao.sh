#!/bin/bash
# Cai dat phan BEN QUA KHOI DONG LAI cho cong vao Linux (H39/G2).
#
# Vi sao can: `nft add element` va `ip addr add` chi song trong bo nho. Neu chi
# lam hai viec do thi cong vao khoi dong lai la TOAN BO khach mat duong vao, im
# lang, va trieu chung se la "sang nay khong ai vao duoc may nua" - khong log
# nao bao, khong canh bao nao keu.
#
# Script nay dat mot unit systemd doc lai /etc/ltt-vps/duong.conf va phat lai
# tung dong sau khi mang va nftables da san sang.
#
# Chay tren CHINH cong vao:  bash cai-dat-cong-vao.sh
set -euo pipefail

TEP=/etc/ltt-vps/duong.conf
AP_DUNG=/usr/local/sbin/ltt-vps-ap-dung

mkdir -p "$(dirname "$TEP")"
touch "$TEP"
chmod 600 "$TEP"

cat > "$AP_DUNG" <<'EOF'
#!/bin/bash
# Phat lai cac duong NAT 1:1 sau khi khoi dong lai. Chay lai duoc.
set -uo pipefail
TEP=/etc/ltt-vps/duong.conf
BANG=ltt
[ -s "$TEP" ] || { echo "khong co duong nao de phat lai"; exit 0; }

WAN=$(ip -o -4 route show default | awk '{print $5; exit}')
[ -n "$WAN" ] || { echo "khong tim thay card WAN"; exit 1; }

# Cho nftables nap xong ruleset goc truoc khi them phan tu vao map.
for _ in $(seq 1 30); do
    nft list map ip "$BANG" vao >/dev/null 2>&1 && break
    sleep 1
done

so=0
while read -r cong noi; do
    [ -n "${cong:-}" ] && [ -n "${noi:-}" ] || continue
    case "$cong" in \#*) continue ;; esac
    ip addr replace "$cong/32" dev "$WAN"
    nft delete element ip "$BANG" vao "{ $cong }" 2>/dev/null || true
    nft delete element ip "$BANG" ra  "{ $noi }"  2>/dev/null || true
    nft add element ip "$BANG" vao "{ $cong : $noi }"
    nft add element ip "$BANG" ra  "{ $noi : $cong }"
    so=$((so + 1))
done < "$TEP"
echo "da phat lai $so duong"
EOF
chmod 755 "$AP_DUNG"

cat > /etc/systemd/system/ltt-vps-duong.service <<'EOF'
[Unit]
Description=LTT VPS - phat lai cac duong NAT 1:1 sau khi khoi dong lai
# Phai chay SAU nftables (ruleset goc + hai map) va sau khi mang co dia chi.
After=network-online.target nftables.service
Wants=network-online.target
Requires=nftables.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/local/sbin/ltt-vps-ap-dung

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ltt-vps-duong.service >/dev/null
echo "da cai unit ltt-vps-duong.service"
systemctl is-enabled ltt-vps-duong.service
