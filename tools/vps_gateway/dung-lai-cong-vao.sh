#!/usr/bin/env bash
#
# Dung LAI toan bo mot cong vao tu mot VPS Debian trang (H39/G9b).
#
#     bash dung-lai-cong-vao.sh <khoa-rieng-wireguard-base64> <pubkey-router>
#
# Chay lai duoc: chay hai lan khong hong gi.
#
# ---------------------------------------------------------------------------
# VI SAO CO TEP NAY
#
# `cai-dat-cong-vao.sh` chi dat phan PHAT LAI cac duong NAT sau khoi dong lai.
# No **khong** dung duoc mot cong vao tu con so khong: thieu WireGuard, thieu
# bo luat nftables nen, thieu chuyen tiep goi.
#
# Nghia la truoc tep nay, cau tra loi cho "cong vao chet thi sao" la mot buoi
# lam bang tay va mot tai lieu khong ai kiem lai bao gio.
#
# Toi tung viet trong ke hoach rang chiu duoc cong-vao-chet "can mua them mot
# VPS $6/thang". **Do la mot ket luan sai.** Rang buoc that hep hon nhieu: IP
# cong khai phai nam tren mot may Vultr (Reserved IP chi gan duoc vao instance
# Vultr, va nha thi khong co IP dinh tuyen duoc). Nen mot cong **chay song song**
# thi dung la can may thu hai -- nhung "dung lai duoc trong vai phut" thi khong.
#
# Reserved IP **khong chet theo may**: go khoi may cu, gan vao may moi, dia chi
# giu nguyen. Cong vao thi gan nhu khong co trang thai. Cong lai: mot con VPS
# moi + tep nay + `cai-dat-cong-vao.sh` = cong vao song lai, $0/thang.
#
# ---------------------------------------------------------------------------
# THU TU DUNG, VA VI SAO
#
# 1. Khoa rieng TRUOC. Router ben nha GHIM khoa cong khai cua cong vao. Dung
#    khoa moi thi router khong bat tay duoc, va trieu chung la "cong vao len roi
#    ma khach van khong vao duoc" -- mot cho rat de mat thi gio. Khoa cu nam o
#    secrets/cong_vao/wg_private.key cua kho ma nguon.
# 2. Chuyen tiep goi. Thieu no thi WireGuard len, bat tay xong, va goi im lang
#    khong di dau ca.
# 3. nftables nen (bang `ltt` + hai map rong). `cai-dat-cong-vao.sh` phat lai
#    cac duong VAO map do; khong co bang thi no phat vao hu khong.
# 4. Cuoi cung moi mo cong 51820 va bat WireGuard.
#
# ---------------------------------------------------------------------------
# CAI CHUA TU DONG, VA NOI THANG
#
# Tep nay khong tao instance Vultr va khong gan lai Reserved IP -- hai viec do
# di qua API, khong qua shell. Chung nam o `tools/vps_dung_lai_cong_vao.py`.
set -euo pipefail

KHOA_RIENG="${1:-}"
PUBKEY_ROUTER="${2:-}"
MANG_KHACH="10.51.0.0/24"
WG_TA="10.51.255.1/24"
WG_ROUTER="10.51.255.2/32"
CONG_WG=51820
BANG=ltt

if [ "$(id -u)" != "0" ]; then echo "Phai chay bang root"; exit 1; fi
if [ -z "$KHOA_RIENG" ] || [ -z "$PUBKEY_ROUTER" ]; then
  echo "Dung: bash dung-lai-cong-vao.sh <khoa-rieng-wg> <pubkey-router>"
  echo
  echo "Khoa rieng lay tu secrets/cong_vao/wg_private.key trong kho ma nguon."
  echo "Dung khoa MOI thi router khong bat tay duoc -- xem chu thich dau tep."
  exit 2
fi

echo "== 1/5 Goi =="
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq wireguard nftables >/dev/null

echo "== 2/5 Chuyen tiep goi =="
cat > /etc/sysctl.d/99-ltt-cong-vao.conf <<'EOF'
# Cong vao la mot bo dinh tuyen: khong bat chuyen tiep thi WireGuard bat tay
# xong roi goi im lang khong di dau ca.
net.ipv4.ip_forward=1
# rp_filter=2 (loose): goi tra ve cho khach di VAO qua WAN va RA qua wg0, tuc
# duong ve khong doi xung. Che do 1 (strict) vut chung di, va trieu chung la
# "ping duoc nhung TCP thi khong".
net.ipv4.conf.all.rp_filter=2
net.ipv4.conf.default.rp_filter=2
EOF
sysctl -q --system

echo "== 3/5 WireGuard =="
mkdir -p /etc/wireguard
umask 077
printf '%s\n' "$KHOA_RIENG" > /etc/wireguard/private.key
chmod 600 /etc/wireguard/private.key
cat > /etc/wireguard/wg0.conf <<EOF
[Interface]
Address = $WG_TA
ListenPort = $CONG_WG
MTU = 1420
# Khoa rieng doc tu file rieng, khong nam trong file cau hinh nay.
PostUp = wg set %i private-key /etc/wireguard/private.key

[Peer]
# VM router ben nha. KHONG khai Endpoint: phia nha chu dong goi ra, cong vao
# hoc dia chi tu cai bat tay den. Nho vay IP dong o nha khong thanh van de.
PublicKey = $PUBKEY_ROUTER
AllowedIPs = $WG_ROUTER, $MANG_KHACH
EOF
chmod 600 /etc/wireguard/wg0.conf

echo "== 4/5 nftables nen =="
#
# Bo luat nay KHONG phai do toi nghi ra — no la ban SAO LUU cua bo luat DANG
# CHAY tren cong vao that (secrets/cong_vao/nftables.conf).
#
# Ban dau toi tu viet lai mot bo "tuong duong". No thieu dung mot dong:
#
#     ip saddr 10.51.0.0/24 oifname "enp1s0" masquerade
#
# Dong do la duong ra cho may CHUA duoc gan IP rieng — luc dang tao, hoac khi
# gan IP that bai. Thieu no thi may len binh thuong va khong ra duoc Internet,
# im lang. Mot script dung lai sinh ra mot cong vao "gan giong" thi TE HON
# khong co script, vi no trong nhu da chay xong.
#
# Sua bo luat that thi phai sao luu lai vao secrets/cong_vao/ VA sua o day.
cat > /etc/nftables.conf <<'NFT'
#!/usr/sbin/nft -f
# KHONG `flush ruleset`: cau do xoa luon luat cua UFW, va khi UFW nap lai
# sau khoi dong lai thi duong ham chet im lang. Chi dung toi bang cua ta.
table ip ltt
delete table ip ltt

# Dung MAP thay vi mot luat cho moi khach: tra cuu O(1) bat ke 5 hay 500 khach.
# Tai lieu hieu nang WireGuard canh bao ro — ruleset cang dai thi ket noi cang
# cham; cach pho bien "moi khach mot luat dnat" chinh la cai bay do. Them khach
# = them MOT phan tu vao map, nguyen tu, khong nap lai ruleset.
table ip ltt {
    map vao  { type ipv4_addr : ipv4_addr ; }   # IP cong khai -> IP noi bo
    map ra   { type ipv4_addr : ipv4_addr ; }   # IP noi bo   -> IP cong khai

    chain prerouting {
        type nat hook prerouting priority dstnat; policy accept;
        dnat to ip daddr map @vao
    }

    chain postrouting {
        type nat hook postrouting priority srcnat; policy accept;
        # Khach co IP rieng: ra bang dung IP do (1:1).
        snat to ip saddr map @ra
        # Khach dung chung: ra bang IP cua gateway.
        ip saddr 10.51.0.0/24 oifname "enp1s0" masquerade
    }

    chain forward {
        type filter hook forward priority mangle; policy accept;
        # Ghim MSS theo MTU that. Thieu buoc nay thi goi lon roi IM LANG va
        # trieu chung la "web nao cung vao duoc tru vai trang".
        tcp flags syn tcp option maxseg size set rt mtu
    }
}
NFT
nft -f /etc/nftables.conf
systemctl enable nftables >/dev/null 2>&1 || true

echo "== 5/5 Mo cong va bat WireGuard =="
# UFW tren anh Debian cua Vultr chan 51820 mac dinh, va cung chan chuyen tiep.
if command -v ufw >/dev/null 2>&1; then
  ufw allow "$CONG_WG"/udp >/dev/null 2>&1 || true
  sed -i 's/^DEFAULT_FORWARD_POLICY=.*/DEFAULT_FORWARD_POLICY="ACCEPT"/' \
      /etc/default/ufw 2>/dev/null || true
  ufw reload >/dev/null 2>&1 || true
fi
systemctl enable wg-quick@wg0 >/dev/null 2>&1 || true
systemctl restart wg-quick@wg0

echo
echo "-- wg0      : $(ip -4 -br addr show wg0 2>/dev/null || echo 'CHUA LEN')"
echo "-- khoa cong khai cua cong vao: $(wg pubkey < /etc/wireguard/private.key)"
echo "   (phai KHOP thu router ghim o [Peer] PublicKey; khac la khach khong vao duoc)"
echo "-- nftables : $(nft list map ip $BANG vao >/dev/null 2>&1 && echo 'bang ltt san sang' || echo 'CHUA CO')"
echo
echo "Con hai viec KHONG lam bang shell duoc, chay tiep:"
echo "  1. bash cai-dat-cong-vao.sh          (phat lai duong NAT sau khoi dong lai)"
echo "  2. python tools\\vps_dung_lai_cong_vao.py --gan-lai-ip"
echo "     (gan lai Reserved IP sang may nay, va mo lai duong cho tung khach)"
